# IBM Cloud Credentials Setup Guide

This guide provides step-by-step instructions for obtaining the necessary IBM Cloud credentials for your project, including API keys, Project IDs, and Cloud Object Storage (COS) credentials.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Creating an IBM Cloud API Key](#creating-an-ibm-cloud-api-key)
3. [Getting Your Project ID](#getting-your-project-id)
4. [Setting Up IBM Cloud Object Storage (COS)](#setting-up-ibm-cloud-object-storage-cos)
5. [Configuring Your Environment](#configuring-your-environment)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have:
- An IBM Cloud account (sign up at https://cloud.ibm.com/registration)
- Access to IBM Cloud Console
- A web browser

---

## Creating an IBM Cloud API Key

An API key is required to authenticate your applications with IBM Cloud services.

### Step 1: Log in to IBM Cloud
1. Navigate to https://cloud.ibm.com
2. Click **Log in** and enter your credentials
3. You'll be redirected to the IBM Cloud Dashboard

### Step 2: Access API Keys Management
1. Click on **Manage** in the top navigation bar
2. Select **Access (IAM)** from the dropdown menu
3. In the left sidebar, click on **API keys**

### Step 3: Create a New API Key
1. Click the **Create** button (or **Create an IBM Cloud API key**)
2. In the dialog box:
   - **Name**: Enter a descriptive name (e.g., "My Project API Key")
   - **Description**: (Optional) Add details about the key's purpose
3. Click **Create**

### Step 4: Save Your API Key
⚠️ **IMPORTANT**: The API key will only be displayed once!

1. A dialog will appear showing your new API key
2. Click **Copy** to copy the key to your clipboard
3. Click **Download** to save it as a JSON file (recommended)
4. Store the key securely - you won't be able to retrieve it again
5. Click **Close**

### API Key Best Practices
- ✅ Store API keys securely (use environment variables, not hardcoded)
- ✅ Use different API keys for different environments (dev, staging, prod)
- ✅ Rotate API keys periodically
- ❌ Never commit API keys to version control
- ❌ Don't share API keys via email or messaging apps

---

## Getting Your Project ID

The Project ID is required for IBM watsonx.ai services.

### Method 1: From watsonx.ai Project

#### Step 1: Access watsonx.ai
1. From the IBM Cloud Dashboard, click the **Navigation menu** (☰) in the top-left
2. Select **AI / Machine Learning**
3. Click on **watsonx.ai** or navigate to https://dataplatform.cloud.ibm.com/wx/home

#### Step 2: Open Your Project
1. Click on **Projects** in the left navigation
2. Select your existing project or create a new one:
   - To create: Click **New project** → **Create an empty project**
   - Enter a name and description
   - Select a storage service (or create one)
   - Click **Create**

#### Step 3: Get the Project ID
1. Once in your project, click on the **Manage** tab
2. Click on the **General** section
3. Find the **Project ID** field
4. Click the **Copy** icon next to the Project ID
5. Save this ID - you'll need it for API calls

### Method 2: From Project Settings

1. In your project, click the **Settings** icon (⚙️) or **Manage** tab
2. Navigate to **General** settings
3. Locate the **Project ID** under project details
4. Copy the alphanumeric string (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

### Project ID Format
- Typically a UUID format: `12345678-1234-1234-1234-123456789abc`
- 36 characters including hyphens
- Used in API endpoints and SDK configurations

---

## Setting Up IBM Cloud Object Storage (COS)

IBM Cloud Object Storage is used for storing and retrieving large amounts of unstructured data.

### Step 1: Create a COS Instance

#### 1.1: Access the Catalog
1. From the IBM Cloud Dashboard, click **Catalog** in the top navigation
2. In the search bar, type "Object Storage"
3. Click on **Object Storage** (or **Cloud Object Storage**)

#### 1.2: Configure the Service
1. **Select a pricing plan**:
   - **Lite**: Free tier with 25 GB storage
   - **Standard**: Pay-as-you-go pricing
   - Choose based on your needs
2. **Service name**: Enter a descriptive name (e.g., "my-project-cos")
3. **Resource group**: Select or create a resource group
4. **Tags**: (Optional) Add tags for organization
5. Click **Create**

### Step 2: Create a Bucket

#### 2.1: Access Your COS Instance
1. From the IBM Cloud Dashboard, click **Resource list** in the navigation menu
2. Expand **Storage**
3. Click on your COS instance name

#### 2.2: Create a New Bucket
1. Click **Create bucket** or **Buckets** → **Create bucket**
2. Choose a bucket type:
   - **Standard**: For frequently accessed data
   - **Vault**: For data accessed once a month or less
   - **Cold Vault**: For data accessed once a year or less
   - **Smart Tier**: Automatically moves data between tiers
3. **Unique bucket name**: Enter a globally unique name (e.g., "my-project-data-bucket")
   - Must be DNS-compliant
   - 3-63 characters
   - Lowercase letters, numbers, hyphens only
4. **Resiliency**: Choose based on your needs:
   - **Cross Region**: Highest availability
   - **Regional**: Single region
   - **Single Data Center**: Lowest cost
5. **Location**: Select your preferred region
6. Click **Create bucket**

### Step 3: Get COS Credentials

#### 3.1: Create Service Credentials
1. In your COS instance, click **Service credentials** in the left sidebar
2. Click **New credential**
3. Configure the credential:
   - **Name**: Enter a descriptive name (e.g., "my-app-credentials")
   - **Role**: Select appropriate role:
     - **Writer**: Read and write access
     - **Reader**: Read-only access
     - **Manager**: Full access including configuration
   - **Service ID**: (Optional) Select or create a service ID
   - **Include HMAC Credential**: Toggle **ON** (required for S3-compatible access)
4. Click **Add**

#### 3.2: View and Copy Credentials
1. Click **View credentials** (dropdown arrow) next to your new credential
2. You'll see a JSON object with important fields:

```json
{
  "apikey": "your-cos-api-key-here",
  "cos_hmac_keys": {
    "access_key_id": "your-access-key-id",
    "secret_access_key": "your-secret-access-key"
  },
  "endpoints": "https://control.cloud-object-storage.cloud.ibm.com/v2/endpoints",
  "iam_apikey_description": "Auto-generated for key...",
  "iam_apikey_name": "my-app-credentials",
  "iam_role_crn": "crn:v1:bluemix:public:iam::::serviceRole:Writer",
  "iam_serviceid_crn": "crn:v1:bluemix:public:iam-identity::...",
  "resource_instance_id": "crn:v1:bluemix:public:cloud-object-storage:global:..."
}
```

3. **Copy the following values**:
   - `apikey`: Your COS API key
   - `cos_hmac_keys.access_key_id`: Access key for S3-compatible access
   - `cos_hmac_keys.secret_access_key`: Secret key for S3-compatible access
   - `resource_instance_id`: Your COS instance ID

### Step 4: Get COS Endpoints

#### 4.1: Find Your Endpoint
1. In your COS instance, click **Endpoints** in the left sidebar
2. Find the endpoint for your bucket's location and resiliency
3. Copy the appropriate endpoint:
   - **Public endpoint**: For access from the internet
   - **Private endpoint**: For access within IBM Cloud (faster, no egress charges)
   - **Direct endpoint**: For access from specific IBM Cloud services

Example endpoints:
- Public: `https://s3.us-south.cloud-object-storage.appdomain.cloud`
- Private: `https://s3.private.us-south.cloud-object-storage.appdomain.cloud`
- Direct: `https://s3.direct.us-south.cloud-object-storage.appdomain.cloud`

### COS Credentials Summary

You'll need these values for your application:

| Credential | Description | Example |
|------------|-------------|---------|
| **COS API Key** | API key for authentication | `abc123...` |
| **Access Key ID** | HMAC access key | `1234567890abcdef` |
| **Secret Access Key** | HMAC secret key | `abcdef1234567890...` |
| **Bucket Name** | Your bucket name | `my-project-data-bucket` |
| **Endpoint** | Service endpoint URL | `s3.us-south.cloud-object-storage.appdomain.cloud` |
| **Resource Instance ID** | COS instance identifier | `crn:v1:bluemix:public:cloud-object-storage:...` |

---