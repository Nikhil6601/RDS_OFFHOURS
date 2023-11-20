variable "aws_region" {
  description = "The AWS region we are targetting"
}

variable "webhook_url" {
  description = "The slack webhook URL"
}

variable "slack_channel" {
  description = "The slack channel to post alerts"
}

variable "work_start_hour" {
  description = "Start hour of work in hour calculation. EX 08"
  type        = string
}

variable "work_start_min" {
  description = "enter the minutes of work in minutes calculation. EX 15, 30"
  type        = string
}

variable "work_end_hour" {
  description = "End hour of work in hour calculation. EX 20"
  type        = string
}

variable "work_end_min" {
  description = "enter the minutes of work in minutes calculation. EX 15, 30"
  type        = string
}

variable "KEY" {
  description = "KEY-value of the rds instance"
  type        = string
}

variable "VALUE" {
  description = "key-Value of the rds instance "
  type        = string
}