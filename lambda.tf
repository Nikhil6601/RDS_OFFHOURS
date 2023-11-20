terraform {
  required_version = "= 1.0.11"
}

provider "aws" {
  region  = var.aws_region
  profile = "saml"
}


terraform {
  backend "s3" {
    bucket         = "comcast-mercloud-offhours-infra-state"
    key            = "ec2_offhours-lambda/tfstate/terraform.tfstate"
    region         = "us-east-1"
  }
}


data "aws_caller_identity" "current" {}

resource "null_resource" "pip_install" {
  triggers = {
    shell_hash = "${sha256(file("${path.module}/requirements.txt"))}"
  }

  provisioner "local-exec" {
    command = "python3 -m pip install -r requirements.txt -t ${path.module}/code"
  }
}


data "archive_file" "code" {
  type        = "zip"
  source_dir  = "${path.module}/code"
  output_path = "${path.module}/code.zip"
  depends_on  = [null_resource.pip_install]
}


data "aws_iam_role" "role" {
  name = "Mercloud_Offhours"
}

resource "aws_lambda_function" "lambda" {
  function_name    = "rds-off-hours-${var.aws_region}"
  handler          = "main.lambda_handler"
  runtime          = "python3.9"
  filename         = data.archive_file.code.output_path
  source_code_hash = data.archive_file.code.output_base64sha256
  role             = data.aws_iam_role.role.arn
  timeout          = 60
  environment {
    variables = {
      SLACK_ENDPOINT  = var.webhook_url
      SLACK_CHANNEL   = var.slack_channel
      WORK_START_HOUR = var.work_start_hour
      WORK_START_MIN = var.work_start_min
      WORK_END_HOUR = var.work_end_hour
      WORK_END_MIN = var.work_end_min
      KEY = var.KEY
      VALUE = var.VALUE
    }
  }
  tags = {
    Role = "rds_offhours"
    Env  = terraform.workspace
  }
}

resource "aws_cloudwatch_event_rule" "on_schedule" {
  name                = "weekday-every-twelve-hours"
  description         = "Fires at 00 and 12 every work day"
  schedule_expression = "cron(55 12,00 ? * * *)"
}

resource "aws_cloudwatch_event_target" "ec2_offhours_everyday" {
  rule      = aws_cloudwatch_event_rule.on_schedule.name
  target_id = "rds_off-hours-${var.aws_region}"
  arn       = aws_lambda_function.lambda.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_check_foo" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.on_schedule.arn
}