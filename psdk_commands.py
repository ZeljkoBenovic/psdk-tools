#!/usr/bin/python3
import argparse
import sys
import os
import subprocess
import signal
import shutil
import platform
import json
# import local git package
sys.path.append(os.path.dirname(__file__)+'/vendor/git')
from git import Repo

from helpers import UserInputBool


class PsdkCommands:
    
  def Run(self):
    
    self.__parser = argparse.ArgumentParser()
    self.__parser.add_argument("-c", "--command",dest="command",default="",help="The command you would like to run against all nodes. For multiple commands \" \" are required. Default: start new chain")
    self.__parser.add_argument("-b", "--branch",dest="branch",default="develop",help="PolygonSDK branch that will be cloned. Default: develop")
    self.__parser.add_argument("-d", "--dir",dest="clone_path",default="/tmp/polygon/polygon-sdk",help="Folder to clone repo into. Default: /tmp/polygon-sdk")
    self.__parser.add_argument("-pd", "--psdk-data",dest="psdk_data",default="/tmp/polygon/data",help="Folder to put the PolygonSDK data files. Default: /tmp/polygon/data")
    self.__parser.add_argument("-pl", "--psdk-logs",dest="psdk_logs",default="/tmp/polygon/logs",help="Folder to put the PolygonSDK log files. Default: /tmp/polygon/logs")
    self.__parser.add_argument("-vn", "--validator-nodes",dest="validators",default=4,help="The number of validator nodes. Default: 4")
    self.__parser.add_argument("-n", "--non-validator-nodes",dest="non_validators",default=2,help="The number of non-validator nodes. Default: 2")
    self.__parser.add_argument("-p", "--l2p-start-port",dest="libp2p_start_port",default=20001,help="The starting port for libp2p. Default: 20001")
    self.__parser.add_argument("-g", "--grpc-start-port",dest="grpc_start_port",default=30001,help="The starting port for libp2p. Default: 20001")
    self.__parser.add_argument("-j", "--json-rpc-start-port",dest="json_rpc_start_port",default=40001,help="The starting port for libp2p. Default: 20001")
    self.__parser.add_argument("-pm", "--premine-address",dest="premine_addresses",default="0x228466F2C715CbEC05dEAbfAc040ce3619d7CF0B",nargs="*",help="Premine addresses. Add multiple addresses with space in between. Default: 0x228466F2C715CbEC05dEAbfAc040ce3619d7CF0B")
    self.__parser.add_argument("-pmf", "--premine-funds",dest="premine_funds",default="1000000000000000000000",help="Funds for the premined addresses. All addresses will have this amount premined. Default: 1000000000000000000000")
    self.__parser.add_argument("-gl", "--block-gas-limit",dest="block_gas_limit",required=False,help="Set block gas limit")
    self.__parser.add_argument("-ms", "--max-slots",dest="max_slots",default="100000",help="Set max slot limit Default: 100000")
    

    self.__args = self.__parser.parse_args()
    
    self.__RunCommand()
    exit()

    
  def __RunCommand(self):
    # run commands in multiple threads

    if self.__args.command == 'start new chain':
      self.__StartNewChain()

    elif self.__args.command == 'stop':
      self.__StopAllServers()

    elif self.__args.command == 'start':
      self.__StartServer()

    else:
      self.__parser.print_help()
    
  # start a brand new chain
  def __StartNewChain(self) -> None:
    # Store user settings to file
    self.__StoreSettings()
    # Fetch branch from repo
    self.__FetchCode()
    # Build repo
    self.__VerifyGo()
    # Init psdk server
    self.__InitPSDKServer()
    # Generate genesis.json
    self.__GenerateGenesisFile()
    # Start polygon-sdk servers
    self.__StartServer()
 
  # fetch git code from the specified branch
  def __FetchCode(self) -> None:
    if os.path.isdir(self.__args.clone_path) and UserInputBool("Existing repo found. Would you like to use the existing repo ? [y/N]"):
      print("Using the existin repo.")
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
  def __VerifyGo(self) -> None:

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
  def __InitPSDKServer(self) -> None:

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
  def __GenerateGenesisFile(self) -> None:
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
  def __StartServer(self) -> None:

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
  def __StopAllServers(self) -> None:

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
  
  # store user settings to file
  def __StoreSettings(self) -> None:
    settings = {}
    settings["command"] = self.__args.command
    settings["branch"] = self.__args.branch
    settings["clone_path"] = self.__args.clone_path
    settings["psdk_data"] = self.__args.psdk_data
    settings["psdk_logs"] = self.__args.psdk_logs
    settings["validators"] = self.__args.validators
    settings["non_validators"] = self.__args.non_validators
    settings["libp2p_start_port"] = self.__args.libp2p_start_port
    settings["grpc_start_port"] = self.__args.grpc_start_port
    settings["json_rpc_start_port"] = self.__args.json_rpc_start_port
    settings["premine_addresses"] = self.__args.premine_addresses
    settings["premine_funds"] = self.__args.premine_funds
    settings["block_gas_limit"] = self.__args.block_gas_limit
    settings["max_slots"] = self.__args.max_slots

    with open(os.path.dirname(__file__)+"/storage/config.json","w") as json_settings:
      json.dump(settings,json_settings,indent=4)
