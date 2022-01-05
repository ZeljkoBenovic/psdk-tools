#!/usr/bin/python3
import sys
import argparse
import os
import json

from environments import Cloud, Localhost

class PsdkCommands:

   
  def Run(self):
    
    self.__parser = argparse.ArgumentParser()

    self.__parser.add_argument("-e","--environment",dest="environment",default="localhost",help="The environment you would like to run the nodes on. Default: localhost ( localhost, cloud, docker, terraform )")

    self.__parser.add_argument("--hosts",dest="hosts",default=[],nargs="*",help="If environment is not local, with this flag you specify space delimited list of ip addresses of hosts.")
    self.__parser.add_argument("-s",dest="ssh_key",default="~/.ssh/id_rsa.pub",help="If environment is not local, we'll need ssh key to authenticate to remote hosts. Default: ~/.ssh/id_rsa_pub")
  
    self.__parser.add_argument("-c", "--command",dest="command",default="",help="The command you would like to run against all nodes. For multiple commands \" \" are required.")
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

    self.__SetEnvironment()
    self.__RunCommand()

    exit()

  def __SetEnvironment(self):

    if self.__args.environment == "localhost":
      # instantiate Localhost class and pass all cli args
      self.__env = Localhost(self.__args)

    elif self.__args.environment == "cloud":
      # exit if no addresses are provided in cli
      if self.__args.hosts == []:
        sys.exit("Invalid host count. For Cloud environment, you need to define ip addresses of hosts")
      # instantiate Cloud class and pass all args
      self.__env = Cloud(self.__args)

    else:
      sys.exit("False environment set. Possible environments: localhost, cloud, docker and terraform")
    

  def __RunCommand(self):
    # run commands in multiple threads

    if self.__args.command == 'start new chain':
      self.__StartNewChain()

    elif self.__args.command == 'stop':
      self.__env._StopAllServers()

    elif self.__args.command == 'start':
      self.__env._StartServer()

    else:
      print("No COMMAND (-c) parameter provided. To get help use -h")
    
  # start a brand new chain
  def __StartNewChain(self) -> None:
    # Store user settings to file
    self.__StoreSettings()
    # Fetch branch from repo
    self.__env._FetchCode()
    # Build repo
    self.__env._VerifyGo()
    # Init psdk server
    self.__env._InitPSDKServer()
    # Generate genesis.json
    self.__env._GenerateGenesisFile()
    # Start polygon-sdk servers
    self.__env._StartServer()

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
    settings["hosts"] = self.__args.hosts
    settings["environment"] = self.__args.environment

    # create storage dir that will hold node info
    if not os.path.isdir(os.path.dirname(__file__)+"/storage"):
      os.mkdir(os.path.dirname(__file__)+"/storage")
    
    with open(os.path.dirname(__file__)+"/storage/config.json","w") as json_settings:
      json.dump(settings,json_settings,indent=4)
