# Variable definitions for Postgres Terraform config
# Issue #5: AgentState + checkpointing

# Note: Variables are defined in main.tf with defaults.
# This file exists for documentation and potential override via terraform.tfvars.

# To override defaults, create a terraform.tfvars file:
#
#   postgres_user     = "myuser"
#   postgres_password = "mysecretpassword"
#   postgres_db       = "mydb"
#   postgres_port     = 5433
