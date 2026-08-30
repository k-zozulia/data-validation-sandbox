resource "aws_s3_bucket" "data" {
  bucket        = "${local.project}-data-${data.aws_caller_identity.current.account_id}"
  force_destroy = true 
  tags          = local.tags
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    id     = "expire-after-1-day"
    status = "Enabled"
    filter {}
    expiration {
      days = 1
    }
  }
}

output "s3_bucket_name" {
  value = aws_s3_bucket.data.bucket
}