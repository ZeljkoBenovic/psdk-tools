from abc import ABC, abstractmethod
import sys
import os
import subprocess
import signal
import shutil
import platform
import json
import concurrent.futures

# import local git package
sys.path.append(os.path.dirname(__file__)+'/vendor/git')
sys.path.append(os.path.dirname(__file__)+'/vendor/paramiko')
from git import Repo
import paramiko

from helpers import UserInputBool


class Environment(ABC):

  @abstractmethod
  def _FetchCode(self):
    pass
  @abstractmethod
  def _VerifyGo(self):
    pass
  @abstractmethod
  def _InitPSDKServer(self):
    pass
  @abstractmethod
  def _GenerateGenesisFile(self):
    pass
  @abstractmethod
  def _StartServer(self):
    pass

class Localhost(Environment):
  
  def __init__(self,args) -> None:
      self.__args = args

  # fetch git code from the specified branch
  def _FetchCode(self) -> None:
    if os.path.isdir(self.__args.clone_path) and UserInputBool("Existing repo found. Would you like to use the existing repo ? [y/N]"):
      print("Using the existing repo.")
      return
    else:
      print(f"Cloning branch {self.__args.branch}...")
      # remove dir if exists
      if os.path.isdir(f"{self.__args.clone_path}"):
        shutil.rmtree(self.__args.clone_path)
      # clone the repo
      Repo.clone_from("https://github.com/0xPolygon/polygon-sdk.git",self.__args.clone_path,branch=self.__args.branch)
      print(f"Branch {self.__args.branch} cloned.")
  
  # verify that go is available
  def _VerifyGo(self) -> None:

    # add existing go binary to path
    os.environ["PATH"] += os.pathsep + "/usr/local/go/bin"
    # and check if go is installed
    go_path = shutil.which("go")
    # check the platform
    os_system = platform.system()

    # install go if not detected
    if go_path == None and os_system == "Linux":
      print("Go not installed. Installing...")
      os.system("cd /tmp && curl -OL https://golang.org/dl/go1.17.5.linux-amd64.tar.gz")
      os.system("sudo tar -C /usr/local -xf /tmp/go1.17.5.linux-amd64.tar.gz")
      os.system("sudo rm /tmp/go1.17.5.linux-amd64.tar.gz")
      # add go binary to path for this session
      os.environ["PATH"] += os.pathsep + "/usr/local/go/bin"
    
    print("Go is installed. Proceeding...")
  
  # initialize psdk server
  def _InitPSDKServer(self) -> None:

    # init variables
    validators = []
    non_validators = []
    data_index = 1

    # create storage dir that will hold node info
    if not os.path.isdir(os.path.dirname(__file__)+"/storage"):
      os.mkdir(os.path.dirname(__file__)+"/storage")

    # change dir to cloned folder
    os.chdir(self.__args.clone_path)
    # install dependances
    subprocess.call(f"go install",shell=True)

    #run init for all validators and append incement suffix for dir name if we don't have json data already
    if os.path.isfile(os.path.dirname(__file__)+"/storage/init-validators.json") and UserInputBool("Existing validator node data found. Would you like to use the existing data ? [y/N]"):
      print("Using existing validator data.")
    else:
      for _ in range(0 , self.__args.validators):
        # delete existing directory if exists
        if os.path.isdir(f"{self.__args.psdk_data}-{data_index}"):
          shutil.rmtree(f"{self.__args.psdk_data}-{data_index}")
        # init new directory and data
        validators.append(json.loads(subprocess.run(f"go run main.go secrets init --json --data-dir {self.__args.psdk_data}-{data_index}",shell=True,capture_output=True).stdout.decode("utf-8").rstrip("\n")))
        data_index += 1
        # write this information to json file
      with open(os.path.dirname(__file__)+"/storage/init-validators.json", "w") as json_file:
        json.dump(validators, json_file, indent=4, sort_keys=True)
      

    #run init for all non validators and append incement suffix for dir name if we don't have json data already
    if os.path.isfile(os.path.dirname(__file__)+"/storage/init-non_validators.json") and UserInputBool("Existing non validator node data found. Would you like to use the existing data ? [y/N]"):
      print("Using existing non validator data.")
    else:
      for _ in range(0,self.__args.non_validators):
         # delete existing directory if exists
        if os.path.isdir(f"{self.__args.psdk_data}-{data_index}"):
          shutil.rmtree(f"{self.__args.psdk_data}-{data_index}")
        # init new directory and data
        non_validators.append(json.loads(subprocess.run(f"go run main.go secrets init --json --data-dir {self.__args.psdk_data}-{data_index}",shell=True,capture_output=True).stdout.decode("utf-8").rstrip("\n")))
        data_index += 1
        # write this information to json file
      with open(os.path.dirname(__file__)+"/storage/init-non_validators.json","w") as json_file:
        json.dump(non_validators,json_file,indent=4,sort_keys=True)

  # generate genesis.json
  def _GenerateGenesisFile(self) -> None:
    # change dir to psdk clone folder
    os.chdir(self.__args.clone_path)

    if os.path.isfile(f"{os.path.dirname(self.__args.psdk_data)}/genesis.json") and UserInputBool("Genesis file detected. Would you like to use the existing genesis.json file? [y/N]"):
      print("Using the existing genesis.json file.")
      return


    # first part of init command
    GenesisInitString = f"go run {self.__args.clone_path}/main.go genesis --consensus ibft"
    # add all validator keys and boot nodes
    for i,node in enumerate(json.load(open(os.path.dirname(__file__)+"/storage/init-validators.json"))):
      GenesisInitString += f" --ibft-validator={node['address']} --bootnode=/ip4/127.0.0.1/tcp/{str(self.__args.libp2p_start_port+i)}/p2p/{node['node_id']}"

    # add premine
    for address in self.__args.premine_addresses:
        GenesisInitString += f" --premine={address}:{str(self.__args.premine_funds)}"

    # set block gas limit
    if self.__args.block_gas_limit:
        GenesisInitString += f" --block-gas-limit {self.__args.block_gas_limit}"

    # now we can create genesis.json
    os.system(GenesisInitString)
    os.system(f"mv {os.curdir}/genesis.json {os.path.dirname(self.__args.psdk_data)}")
    print(f"Genesis file generated at {os.path.dirname(self.__args.psdk_data)}")

  # start psdk server   
  def _StartServer(self) -> None:

    # init vars
    data_index = 0
    validator_pids = []
    non_validator_pids = []

    # get user settings from json file
    with open(os.path.dirname(__file__)+"/storage/config.json") as json_settings:
      settings = json.load(json_settings)
    

    # add go binary to path for this session
    os.environ["PATH"] += os.pathsep + "/usr/local/go/bin"

    # change dir to clone dir
    os.chdir(settings['clone_path'])

    # run server command for every validator and redirect the output to file
    for _ in json.loads(open(os.path.dirname(__file__)+"/storage/init-validators.json").read()):
      cmd = f"go run main.go server --max-slots={settings['max_slots']} --data-dir {settings['psdk_data']}-{data_index+1} --chain {os.path.dirname(settings['psdk_data'])}/genesis.json --grpc 127.0.0.1:{settings['grpc_start_port']+data_index} --libp2p 127.0.0.1:{settings['libp2p_start_port']+data_index} --jsonrpc 127.0.0.1:{settings['json_rpc_start_port']+data_index} --seal --log-level debug"
      validator_pids.append(subprocess.Popen(cmd, preexec_fn=os.setsid, shell=True, stdout=open(f"{os.path.dirname(settings['psdk_data'])}/node-{data_index+1}.log","w"), stderr=open(f"{os.path.dirname(settings['psdk_data'])}/node-{data_index+1}.log","w")).pid)
      data_index += 1
    # run server command for every non validator and redirect the output to file
    for _ in json.loads(open(os.path.dirname(__file__)+"/storage/init-non_validators.json").read()):
      cmd = f"go run main.go server --max-slots={settings['max_slots']} --data-dir {settings['psdk_data']}-{data_index+1} --chain {os.path.dirname(settings['psdk_data'])}/genesis.json --grpc 127.0.0.1:{settings['grpc_start_port']+data_index} --libp2p 127.0.0.1:{settings['libp2p_start_port']+data_index} --jsonrpc 127.0.0.1:{settings['json_rpc_start_port']+data_index} --log-level debug"
      non_validator_pids.append(subprocess.Popen(cmd, preexec_fn=os.setsid, shell=True, stdout=open(f"{os.path.dirname(settings['psdk_data'])}/node-{data_index+1}.log","w"), stderr=open(f"{os.path.dirname(settings['psdk_data'])}/node-{data_index+1}.log","w")).pid)
      data_index += 1
    
    # save PIDs to file
    with open(os.path.dirname(__file__)+"/storage/validator-pids.json","w") as json_file:
      json.dump(validator_pids,json_file,indent=4)
        
    with open(os.path.dirname(__file__)+"/storage/non_validator-pids.json","w") as json_file:
      json.dump(non_validator_pids,json_file,indent=4)

    print(f"All servers started! Check the logs in {os.path.dirname(settings['psdk_data'])} for activity.")

  # stop psdk server
  def _StopAllServers(self) -> None:

    if not os.path.isfile(os.path.dirname(__file__)+"/storage/validator-pids.json") or not os.path.isfile(os.path.dirname(__file__)+"/storage/non_validator-pids.json"):
      print("No servers running. You can't kill any server processes!")
      return
    
    # kill portgroup of PIDs returned from running the server
    for pid in json.loads(open(os.path.dirname(__file__)+"/storage/validator-pids.json").read()):
      os.killpg(os.getpgid(pid),signal.SIGTERM)
    
    # remove PIDs file
    os.remove(os.path.dirname(__file__)+"/storage/validator-pids.json")
 
    # kill portgroup of PIDs returned from running the server
    for pid in json.loads(open(os.path.dirname(__file__)+"/storage/non_validator-pids.json").read()):
      os.killpg(os.getpgid(pid),signal.SIGTERM)
      
    # remove PIDs file
    os.remove(os.path.dirname(__file__)+"/storage/non_validator-pids.json")

    
    print("All servers stopped!")

class Cloud(Environment):

  def __init__(self,args) -> None:
      self.__args = args
  
  def _FetchCode(self) -> None:
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
      executor.map(self.__FetchCodeThread, self.__args.hosts)
  
  def _VerifyGo(self):
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
      executor.map(self.__VerifyGoThread, self.__args.hosts)
  
  
  
  def __FetchCodeThread(self,host: str) -> None:
    # setup ssh client
    ssh = paramiko.SSHClient()
    ssh.get_host_keys().clear()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
      ssh.connect(username=self.__args.ssh_user, hostname=host, key_filename=self.__args.ssh_key,timeout=5)
    except BaseException as e:
      print(f"Could not connect to {host} . ERROR: {e}")
      

    # remove clone dir if already exists
    ssh.exec_command("rm -R "+self.__args.clone_path)
    ssh.exec_command("mkdir -p "+self.__args.clone_path)

    # check if git is installed
    _,out,_ = ssh.exec_command("which git")
    if not out.read():
      # install git ubuntu
      ssh.exec_command("sudo apt install git")
    
    #clone branch
    ssh.exec_command(f"cd {self.__args.clone_path} && git clone https://github.com/0xPolygon/polygon-sdk.git -b {self.__args.branch} .")

    print(f"Branch {self.__args.branch} on {host} is cloned.")

    ssh.close()
    return

  def __VerifyGoThread(self,host: str) -> None:
     # setup ssh client
    ssh = paramiko.SSHClient()
    ssh.get_host_keys().clear()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
      ssh.connect(username=self.__args.ssh_user, hostname=host, key_filename=self.__args.ssh_key,timeout=5)
    except BaseException as e:
      print(f"Could not connect to {host} . ERROR: {e}")

    _,out,_ = ssh.exec_command("which go")
    if not out.read():
      # install go ubuntu
      ssh.exec_command("sudo snap install go --classic")
      print(f"Go is installed on {host}. Proceeding...")
    else:
      print(f"Go already installed on {host}. Proceeding...")
    
    ssh.close()
    return
    
  

  
  def _InitPSDKServer(self):
    print("Init psdk")
  
  def _GenerateGenesisFile(self):
    print("Generate Genesis")
  
  def _StartServer(self):
    print("Start server")