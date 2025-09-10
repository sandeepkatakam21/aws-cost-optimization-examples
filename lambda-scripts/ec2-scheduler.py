#!/usr/bin/env python3
"""
AWS EC2 Scheduler Lambda Function

This Lambda function provides automated EC2 instance start/stop scheduling
to optimize AWS costs by running instances only when needed.

Features:
- Schedule-based EC2 instance management (start/stop)
- Support for tag-based instance filtering
- Customizable by instance IDs or tags
- Integration with AWS CloudWatch Events for automated triggering
- Cost optimization through intelligent instance lifecycle management

Author: AWS Cost Optimization Team
Version: 1.0
Last Updated: September 2025

CloudWatch Events Integration:
  Create CloudWatch Events rules to trigger this Lambda function:
  - Schedule Expression: rate(1 hour) or cron(0 9 * * MON-FRI *)
  - Target: This Lambda function
  - Input: JSON payload with action and instance filters

Required IAM Permissions:
  - ec2:DescribeInstances
  - ec2:StartInstances
  - ec2:StopInstances
  - logs:CreateLogGroup
  - logs:CreateLogStream
  - logs:PutLogEvents

Environment Variables:
  - DEFAULT_ACTION: 'start' or 'stop'
  - TAG_KEY: Tag key for filtering instances (default: 'Schedule')
  - TAG_VALUE: Tag value for filtering instances
  - INSTANCE_IDS: Comma-separated list of specific instance IDs
"""

import json
import boto3
import logging
from typing import List, Dict, Any
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize EC2 client
ec2_client = boto3.client('ec2')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda function handler for EC2 scheduling operations.
    
    Args:
        event (dict): Lambda event payload containing:
            - action: 'start' or 'stop'
            - instance_ids: List of specific instance IDs (optional)
            - tag_filters: Dict of tag key-value pairs for filtering (optional)
        context: Lambda runtime context
    
    Returns:
        dict: Response containing operation results and affected instances
    """
    try:
        # Extract parameters from event or environment
        action = event.get('action', os.getenv('DEFAULT_ACTION', 'stop'))
        instance_ids = event.get('instance_ids', [])
        tag_filters = event.get('tag_filters', {})
        
        # If no specific instances provided, use environment variables
        if not instance_ids and not tag_filters:
            env_instance_ids = os.getenv('INSTANCE_IDS', '')
            if env_instance_ids:
                instance_ids = [id.strip() for id in env_instance_ids.split(',')]
            
            tag_key = os.getenv('TAG_KEY', 'Schedule')
            tag_value = os.getenv('TAG_VALUE')
            if tag_value:
                tag_filters = {tag_key: tag_value}
        
        # Get instances to operate on
        target_instances = get_target_instances(instance_ids, tag_filters)
        
        if not target_instances:
            logger.info("No instances found matching the criteria")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No instances found matching the criteria',
                    'affected_instances': []
                })
            }
        
        # Perform the requested action
        if action.lower() == 'start':
            result = start_instances(target_instances)
        elif action.lower() == 'stop':
            result = stop_instances(target_instances)
        else:
            raise ValueError(f"Invalid action: {action}. Must be 'start' or 'stop'")
        
        logger.info(f"Successfully {action}ed {len(target_instances)} instances")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f"Successfully {action}ed {len(target_instances)} instances",
                'action': action,
                'affected_instances': target_instances,
                'results': result
            })
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f"Lambda execution failed: {str(e)}"
            })
        }


def get_target_instances(instance_ids: List[str] = None, tag_filters: Dict[str, str] = None) -> List[str]:
    """
    Retrieve list of EC2 instances based on provided filters.
    
    Args:
        instance_ids: List of specific instance IDs
        tag_filters: Dictionary of tag key-value pairs for filtering
    
    Returns:
        List of instance IDs matching the criteria
    """
    try:
        filters = []
        
        # Add tag filters
        if tag_filters:
            for key, value in tag_filters.items():
                filters.append({
                    'Name': f'tag:{key}',
                    'Values': [value]
                })
        
        # Query instances
        if instance_ids:
            response = ec2_client.describe_instances(
                InstanceIds=instance_ids,
                Filters=filters
            )
        else:
            response = ec2_client.describe_instances(Filters=filters)
        
        # Extract instance IDs
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append(instance['InstanceId'])
        
        return instances
        
    except Exception as e:
        logger.error(f"Error getting target instances: {str(e)}")
        raise


def start_instances(instance_ids: List[str]) -> Dict[str, Any]:
    """
    Start the specified EC2 instances.
    
    Args:
        instance_ids: List of instance IDs to start
    
    Returns:
        Response from EC2 start_instances API call
    """
    try:
        logger.info(f"Starting instances: {instance_ids}")
        response = ec2_client.start_instances(InstanceIds=instance_ids)
        return response
        
    except Exception as e:
        logger.error(f"Error starting instances: {str(e)}")
        raise


def stop_instances(instance_ids: List[str]) -> Dict[str, Any]:
    """
    Stop the specified EC2 instances.
    
    Args:
        instance_ids: List of instance IDs to stop
    
    Returns:
        Response from EC2 stop_instances API call
    """
    try:
        logger.info(f"Stopping instances: {instance_ids}")
        response = ec2_client.stop_instances(InstanceIds=instance_ids)
        return response
        
    except Exception as e:
        logger.error(f"Error stopping instances: {str(e)}")
        raise


# Example usage and testing
if __name__ == "__main__":
    # Example event for testing
    test_event = {
        "action": "stop",
        "tag_filters": {
            "Environment": "development",
            "Schedule": "business-hours"
        }
    }
    
    # Uncomment to test locally
    # result = lambda_handler(test_event, None)
    # print(json.dumps(result, indent=2))
    pass
