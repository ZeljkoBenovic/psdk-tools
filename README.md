# psdk-tools
PolygonSDK Tools

Python script for fast spinup of PolygonSDK nodes on localhost for testing and development.

## Usage:
- install python3 on your system
- clone repo
- run pdsk-tools.py with the following options:
  - -c *COMMAND*: "start new server", "start", "stop"
  - -b *BRANCH*: branch name you would like to clone
  - -pm *PREMINE ADDRESSES*: space delimited addressed that shoud have premined funds

## Example
To quickly run a 4 validator and 2 non validator nodes on localhost do the following:
- install python3 on your system if not already present ( expected python interpreter path /usr/bin/python3 )
- clone this repo: ``` https://github.com/ZeljkoBenovic/psdk-tools.git ```
- run command: ``` psdk-tools/psdk-tools.py -c "start new chain" ```
- After a few min/sec you should have a working cluster

## Tested on:
- Ubuntu 20.04
  