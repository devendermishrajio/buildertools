#!/usr/bin/python

import sys
import yaml
from subprocess import call
import os

def get_selected_node(cp_yaml):
  node_file = open(cp_yaml, "r")
  cp_data = yaml.load(node_file)
  node_file.close()
  cp_nodes = cp_data["compute_nodes"]
  return (filter(lambda x: x["name"]==cp_node, cp_nodes))[0]

def generate_compute_inventory(compute_inventory, selected_node):
  inv_file = open(compute_inventory, "w")
  inv_file.write("["+selected_node["name"]+"]\n"+selected_node["host"]+"\n")
  inv_file.close()

def run_ansible(inventory, playbook, username="", limit="", extra_vars=""):
  call_list = ["ansible-playbook", "-i", inventory, playbook]

  if username != "":
    call_list.extend(["-u", username])

  if limit != "":
    call_list.extend(["-l", limit])

  if extra_vars != "":
    call_list.extend(["--extra-vars", extra_vars])

  ret = call(call_list)
  if ret != 0:
    raise Exception('no-zero-code', 'ansible-failed')

def run_python(pythonfile, args):
  call_list = ["python", pythonfile]
  call_list.extend(args)
  ret = call(call_list)
  if ret != 0:
    raise Exception('no-zero-code', 'python-failed')

if __name__ == "__main__":
  if len(sys.argv) < 3:
    sys.stderr.write("Insufficient argument")
    sys.exit(-1)

  cp_yaml = sys.argv[1]
  cp_node = sys.argv[2]

  inventory = "inventory"
  if len(sys.argv) >= 4:
    inventory = sys.argv[3]

  user_name = ""
  if len(sys.argv) >= 5:
    user_name = sys.argv[4]

  selected_node = get_selected_node(cp_yaml)
  compute_inventory = selected_node["name"]+".inventory"
  generate_compute_inventory(compute_inventory, selected_node)

  run_ansible(compute_inventory,"bootstrap.yml")
  #print "Test %s"%(selected_node["host"]+" "+selected_node["name"])
  run_ansible(inventory,"add_line_in_file.yml", extra_vars="file=/etc/hosts line=\"%s\""%(selected_node["host"]+" "+selected_node["name"]))
  run_python("apply_changes.py", ["ntp-infile", compute_inventory, "compute_team", cp_node])
  run_ansible(compute_inventory,"install_certs.yml")

  certs=[
          "vpc.ind-west-1.staging.jiocloudservices.com",
          "iam.ind-west-1.staging.jiocloudservices.com",
          "iam.ind-west-1.staging.deprecated.jiocloudservices.com",
          "sbs.ind-west-1.staging.jiocloudservices.com"
        ]

  for cert in certs:
    run_ansible(compute_inventory, "install_certs.yml", extra_vars="cert_name=%s jiocloud_cert=certs/%s.crt"%(cert, cert))

  run_ansible(compute_inventory,"cp.yml")
  run_ansible(compute_inventory,"run_userdata.yml")
  run_ansible(compute_inventory,"check_compute.yml")
  run_ansible(compute_inventory,"sbs.yml")
  run_python("apply_changes.py", ["zmq-infile", compute_inventory, "compute_team"])
  run_python("apply_changes.py", ["computeinfile", compute_inventory, "compute_team"])

  ##run_ansible(inventory,"bootstrap.yml", username=user_name, limit=cp_node)
  ##run_ansible(inventory,"add_line_in_file.yml", extra_vars="\"file=/etc/hosts line=%s\""%(selected_node["host"]+" "+selected_node["name"]), username=user_name)
  ##run_python("apply_changes.py", ["ntp-infile", compute_inventory, "vagrant", cp_node])
  ##run_ansible(inventory,"install_certs.yml", username=user_name, limit=cp_node)
  ##for cert in certs:
  ##  run_ansible(compute_inventory, "install_certs.yml", extra_vars="cert_name=%s jiocloud_cert=certs/%s.crt"%(cert, cert))
  ##run_ansible(inventory,"cp.yml", username=user_name, limit=cp_node)
  ##run_ansible(inventory,"run_userdata.yml", username=user_name, limit=cp_node)
  ##run_ansible(inventory,"check_compute.yml", username=user_name, limit=cp_node)
  ##run_ansible(inventory,"sbs.yml", username=user_name, limit=cp_node)
  ##run_python("apply_changes.py", ["zmq-infile", compute_inventory, "vagrant"])
  ##run_python("apply_changes.py", ["computeinfile", compute_inventory, "vagrant"])

  os.unlink(compute_inventory)
