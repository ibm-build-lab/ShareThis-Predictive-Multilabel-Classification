"""IBM Cloud Object Storage file reader utility"""
import types
import pandas as pd
from typing import Optional
from botocore.client import Config
import ibm_boto3


class COSReader:
    """Utility class for reading files from IBM Cloud Object Storage"""
    
    def __init__(
        self,
        api_key: str,
        endpoint_url: str,
        auth_endpoint: str = "https://iam.cloud.ibm.com/identity/token"
    ):
        """
        Initialize COS client
        
        Args:
            api_key: IBM Cloud API key
            endpoint_url: COS endpoint URL
            auth_endpoint: IAM authentication endpoint
        """
        self.cos_client = ibm_boto3.client(
            service_name='s3',
            ibm_api_key_id=api_key,
            ibm_auth_endpoint=auth_endpoint,
            config=Config(signature_version='oauth'),
            endpoint_url=endpoint_url
        )
    
    def read_csv(self, bucket: str, object_key: str) -> pd.DataFrame:
        """
        Read CSV file from COS bucket
        
        Args:
            bucket: COS bucket name
            object_key: Object key/path in the bucket
            
        Returns:
            DataFrame with the CSV data
        """
        # Get object from COS
        body = self.cos_client.get_object(Bucket=bucket, Key=object_key)['Body']
        
        # Add missing __iter__ method for pandas compatibility
        if not hasattr(body, "__iter__"):
            def __iter__(self):
                return 0
            body.__iter__ = types.MethodType(__iter__, body)
        
        # Read CSV
        df = pd.read_csv(body)
        return df
    
    def file_exists(self, bucket: str, object_key: str) -> bool:
        """
        Check if a file exists in COS bucket
        
        Args:
            bucket: COS bucket name
            object_key: Object key/path in the bucket
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.cos_client.head_object(Bucket=bucket, Key=object_key)
            return True
        except Exception:
            return False