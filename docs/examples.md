# How to use
Set up in Django Admin

## Client layer
The client layer allows you to perform API / SFTP / Database operations directly.

### API
```python
# Example: Making an API request using a Connection instance

from django_filip.models import Connection

# Retrieve a configured connection from the admin
connection = Connection.objects.get(id=1)

# Use the client to make requests
response = connection.client.get("v1/objects/suppliers?param=1")

response.raise_for_status()

# Convert to list of dicts
response = response.json()

# Output the response
for item in response:
    print(item)
```

### Database
```python
# Example: Making a database query using a Connection instance

from django_filip.models import Connection

query = """
    Insert query here
    """

# Retrieve a configured connection from the admin
connection = Connection.objects.get(id=1)

# Use the client to execute the query
response = connection.client.execute_query(query)

# Output the response
print(response)
```

### SFTP

Uploading files:

```python
# Retrieve a configured connection from the admin
connection = Connection.objects.get(id=1)

# Upload from Django FileField
with document.file.open('rb') as file:
    response = connection.client.upload(file, '/remote/path', 'document.pdf')

# Upload from bytes
response = connection.client.upload(b'Hello, World!', '/remote/path', 'text.txt')

# Upload from StringIO/BytesIO
from io import BytesIO
buffer = BytesIO(b'CSV,data,here')
buffer.seek(0)
response = connection.client.upload(buffer, '/remote/path', 'data.csv')

# Reuse directory for multiple files
report_dir = '/uploads/reports'
response1 = connection.client.upload(file1, report_dir, 'jan.pdf')
response2 = connection.client.upload(file2, report_dir, 'feb.pdf')
```

Listing dirs and files:
```python
# Retrieve a configured connection from the admin
connection = Connection.objects.get(id=1)

# List the root directory
response = connection.client.list_dir()
print(response)

# List a sub directory
response = connection.client.list_dir('sub_directory')
print(response)
```


Downloading files:

```python
# Retrieve a configured connection from the admin
connection = Connection.objects.get(id=1)

# Download a file to disk
file = connection.client.download_to_disk('/remote/path/file.txt', '/tmp/file.txt')

# Download a file to memory, and write the file to disk
file_object = connection.client.download_to_memory('/remote/path/file.txt')
local_file_path = '/tmp/file.txt'
with open(local_file_path, 'wb') as f:
    f.write(file_object.read())

# Download to memory (for processing)
file_buffer = connection.client.download_to_memory('/remote/path/file.txt')
content = file_buffer.read().decode('utf-8')
```