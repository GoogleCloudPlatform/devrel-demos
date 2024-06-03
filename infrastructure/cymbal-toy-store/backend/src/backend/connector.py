# Copyright 2024 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.cloud.sql.connector import Connector, IPTypes
from google.cloud import secretmanager
import pg8000
import ssl
import sqlalchemy


def get_secret(secret_id:str, project_id: str) -> str: 
    client = secretmanager.SecretManagerServiceClient()
    name = client.secret_version_path(project_id, secret_id, "latest")
    response = client.access_secret_version(request={"name": name})
    payload = response.payload.data.decode("UTF-8")
    return payload


def connect_with_connector(
    instance_connection_name: str,
    db_name: str, 
    db_user: str,
    db_password: str) -> sqlalchemy.engine.base.Engine:
    """
    Initializes a connection pool for a Cloud SQL instance of Postgres.

    Uses the Cloud SQL Python Connector package.
    """
    # initialize Cloud SQL Python Connector object
    connector = Connector()

    def getconn() -> pg8000.dbapi.Connection:
        conn: pg8000.dbapi.Connection = connector.connect(
            instance_connection_name,
            "pg8000",
            user=db_user,
            password=db_password,
            db=db_name,
            ip_type=IPTypes.PUBLIC,
        )
        return conn

    # The Cloud SQL Python Connector can be used with SQLAlchemy
    # using the 'creator' argument to 'create_engine'
    pool = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        # [START_EXCLUDE]
        # Pool size is the maximum number of permanent connections to keep.
        pool_size=5,
        # Temporarily exceeds the set pool_size if no connections are available.
        max_overflow=2,
        # The total number of concurrent connections for your application will be
        # a total of pool_size and max_overflow.
        # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
        # new connection from the pool. After the specified amount of time, an
        # exception will be thrown.
        pool_timeout=30,  # 30 seconds
        # 'pool_recycle' is the maximum number of seconds a connection can persist.
        # Connections that live longer than the specified amount of time will be
        # re-established
        pool_recycle=1800,  # 30 minutes
        # [END_EXCLUDE]
    )
    return pool

def connect_with_tcp(instance_host: str, db_name: str, db_user: str, db_password: str, db_port: int) -> sqlalchemy.engine.base.Engine:
    #SSL
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE    
    pool = sqlalchemy.create_engine(
        # Equivalent URL:
        # postgresql+pg8000://<db_user>:<db_pass>@<INSTANCE_HOST>:<db_port>/<db_name>
        sqlalchemy.engine.url.URL.create(
            drivername="postgresql+pg8000",
            username=db_user,
            password=db_password,
            host=instance_host,
            port=db_port,
            database=db_name,
        ),
        # [START_EXCLUDE]
        # [START alloydb_sqlalchemy_limit]
        # Pool size is the maximum number of permanent connections to keep.
        pool_size=5,
        # Temporarily exceeds the set pool_size if no connections are
        # available.
        max_overflow=2,
        # The total number of concurrent connections for your application will
        # be a total of pool_size and max_overflow.
        # [END alloydb_sqlalchemy_limit]
        # [START alloydb_sqlalchemy_backoff]
        # SQLAlchemy automatically uses delays between failed connection
        # attempts, but provides no arguments for configuration.
        # [END alloydb_sqlalchemy_backoff]
        # [START alloydb_sqlalchemy_timeout]
        # 'pool_timeout' is the maximum number of seconds to wait when
        # retrieving a new connection from the pool. After the specified
        # amount of time, an exception will be thrown.
        pool_timeout=30,  # 30 seconds
        # [END alloydb_sqlalchemy_timeout]
        # [START alloydb_sqlalchemy_lifetime]
        # 'pool_recycle' is the maximum number of seconds a connection can
        # persist. Connections that live longer than the specified amount
        # of time will be re-established
        pool_recycle=1800,  # 30 minutes
        # [END alloydb_sqlalchemy_lifetime]
        # [START SSL]
        connect_args={"ssl_context": ssl_context},
        # [END SSL]
        # [END_EXCLUDE]
    )
    return pool


