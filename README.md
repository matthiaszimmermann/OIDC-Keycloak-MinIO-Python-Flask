# MinIO OIDC Keycloak Python Flask

Setup Ingredients

* MinIO
* OIDC
* Keycloak
* Python
* Docker
* curl
* jq

## Start with Keycloak

Start a dockerized Keycloack container following the steps outlined in the Keycloak, OIDC, Flask [Github repository](https://github.com/matthiaszimmermann/Keycloak-OIDC-Python-AuthN-AuthZ)

Start with followoing the steps until you have Keycloak up and running with realm `acme` and you can successfully login with users `alice` and `bob`.

Now we will need the following Keycloak additions

* Client `minio`
* Groups `acme_user` and `acme_super_user`

### Add Keycloak Client "minio"

1. Log into your Keycloak UI using user `admin`
2. Add a client `minio` 
3. Switch to tab "Roles" and add roles `minioUser` and `minioSuperuser`
4. Switch to tab "Mappers" and add mapper `minio_mapper` with mapper type `User Client Role`, client id  `minio`, token claim name `policy`

The role names `minioUser` and `minioSuperuser` will be used on the minio side to link to the S3 bucket access policies using as simple string match.
The semantics of these roles will be defined on the minio side. 
For keycloak these are just simple strings without any semantic meaning.

As a result you should end up with the following setup

```bash
Clients + 'minio' + Credentials + Client Authenticator 'Client Id and Secret'
                  |             + Secret 'c12 ... 2a2'
                  + Roles ------+ 'minioSuperuser'
                  |             + 'minioUser'
                  + Mappers ----+ 'minio_mapper' + Protocol 'openid-connect'
                                                 + Name 'minio_mapper'
                                                 + Mapper Type 'User Client Role'
                                                 + Client ID 'minio'
                                                 + Token Claim Name 'policy'
```

The token claim name `policy` will be used by Keycloak to insert a custom claim attribute into the JWT bearer token that will hold role names `minioUser` and/or `minioSuperuser` as values.

### Add Keycloak Groups "acme_user" and "acme_super_user"

1. Log into your Keycloak UI using user `admin`
2. Add group `acme_user`
3. Switch to tab "Role Mappings" and in drop down box "Client Roles" select entry `minio`
4. Add available role `minioUser` so it in box "Assigned Roles"
5. Add group `acme_super_user`
3. Switch to tab "Role Mappings" and in drop down box "Client Roles" select entry `minio`
4. Add available role `minioSuperuser` so it in box "Assigned Roles"

As a result you should end up with the following setup

```bash
Groups + 'acme_super_user' + Role Mappings + Client Roles + 'minio'
       |                                                  + Assigned Roles + 'minioSuperuser'
       + 'acme_user' ------+ Role Mappings + Client Roles + 'minio'
                                                          + Assigned Roles + 'minioUser'
```

### Assign Groups to "alice" and "bob"

1. Log into your Keycloak UI using user `admin`
2. Under "Users" select user `alice`
3. Switch to tab "Groups" 
4. From the available groups select `acme_super_user` and click "Join"
5. Under "Users" select user `bob`
6. Switch to tab "Groups" 
7. From the available groups select `acme_user` and click "Join"

```bash
Users + 'alice' + Groups + 'acme_super_user'
      + 'bob'   + Groups + 'acme_user'
```

### Verify Keycloak Setup

To verify the setup we use the Keycloak REST api to create a JWT bearer access token for user `alice` using the curl command shown below.

The client secret value can be obtained from the Keycloak UI under client `minio` in tab "Credentials"

```bash
CLIENT_SECRET=c12506a9-d2a3-4718-8277-4abab500b2a2
PASSWORD_ALICE=password_alice
curl -s \
  -d "client_id=minio" -d "client_secret=$CLIENT_SECRET" \
  -d "username=alice" -d "password=$PASSWORD_ALICE" \
  -d "grant_type=password" \
  "http://localhost:8080/auth/realms/acme/protocol/openid-connect/token" | jq -r '.access_token'
```

That should print a longish encoded bearer token similar to 

```bash
eyJhbGciOi ... xKoA
```

Check the content using some [JWT browser](https://jwt.io/).
WARNING: Never use some online tool with productive token content!

The plain text token content should the look similar to the example below.

```json
{
  "exp": 1631377776,
  "iat": 1631377476,
  "jti": "c1ec05e0-05be-4234-9052-08fd03cd13c0",
  "iss": "http://localhost:8080/auth/realms/acme",

...
  "scope": "email profile",
  "sid": "1592e5e9-6910-476f-a358-811b96069b8d",
  "email_verified": false,
  "name": "Alice Anderson",
  "preferred_username": "alice",
  "given_name": "Alice",
  "family_name": "Anderson",
  "email": "alice@acme.com",
  "policy": [
    "minioSuperuser"
  ]
}
```

The important part is that attribute `preferred_username` matches with the intended user (`alice` in our case) and that attribute `policy` holds value(s) that match with the client roles entered for client `minio` (`minioSuperuser` in our case).

## S3/MinIO Access Policies

Access control with MinIO works via canned policies. 
Out-of-the-box MinIO has canned policies like 

* `readonly`
* `writeonly`
* `readwrite`

These policies apply to all buckets globally and are not suitable for more fine grained access policies.

### Start the MinIO Server

The minio server setup is included in the `docker run` command shown below.

```bash 
docker run \
-e 'MINIO_ROOT_USER=accesskey' \
-e 'MINIO_ROOT_PASSWORD=secretkey' \
-e 'MINIO_IDENTITY_OPENID_CONFIG_URL=http://192.168.105.112:8080/auth/realms/acme/.well-known/openid-configuration' \
-e 'MINIO_IDENTITY_OPENID_CLIENT_ID=minio' \
-e 'MINIO_IDENTITY_OPENID_CLIENT_SECRET=c12506a9-d2a3-4718-8277-4abab500b2a' \
-e 'MINIO_IDENTITY_OPENID_CLAIM_NAME=policy' \
-v /Users/docker/data/minio_kcl:/data \
-p 9002:9000 \
-d \
minio/minio server /data
```

### Start and use the MinIO Client

The [MinIO client](https://docs.min.io/docs/minio-client-complete-guide) is needed to manage/upload custom policies for the intended setup.
Download and run the MinIO client `mc`.

```bash
docker pull minio/mc
docker run -it --rm --entrypoint=/bin/bash minio/mc
```

Inside mc container add the local minio server via name `minio`.
Use the IP address and port that you used to deploy the MinIO server.

In case your MinIO server is running on localhost you still need the IP address of the localhost.
You may be obtain the IP address using `ifconfig | grep inet` or similar tools.

```bash
mc config host add minio http://192.168.105.112:9002 accesskey secretkey
```

Now use mc to interact with the minio instance.
Let's start with creating two buckets `bucket-a` and `bucket-b`.

```bash
mc mb minio/bucket-a
mc mb minio/bucket-b
mc ls minio
```

Next add some inital content to the buckets.
At the same time we can check the up- and download funcionality.

```bash
echo "hello world!" > hello.txt
mc cp hello.txt minio/bucket-a/hello.a.txt
mc cp hello.txt minio/bucket-b/hello.b.txt
mc ls minio/bucket-a
mc cp minio/bucket-a/hello.a.txt hello.download.txt
cksum hello.*txt
```

### Check existing Canned Policies

Fine graned MinIO access control can be achieved via canned policies.
See [S3 access policies](https://docs.min.io/minio/baremetal/security/minio-identity-management/policy-based-access-control.html#minio-policy-actions), and or [AWS S3 examples](https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-policies-s3.html) for some background.

For a concrete example look at the full definition for the MinIO out-of-the-box canned policy `readwrite`.

```bash
mc admin policy info minio readwrite
```

This prodces the following output

```bash
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:*"],"Resource":["arn:aws:s3:::*"]}]}
```

As shown above the policy `readwrite` allows all S3 actions available on all buckets available.

### Create Custom Canned Policies. 

* Users with policy `minio_superuser.json` have more or less unrestricted access to buckets `bucket-a` and `bucket-b` but not on any other buckets.
* Users with policy `minio_user.json` have read-write access to bucket `bucket-a` and only read access to `bucket-b` but not on any other buckets.

```bash
cat > minio_superuser.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject",        
        "s3:DeleteObject"
      ],
      "Effect": "Allow",
      "Resource": [
        "arn:aws:s3:::bucket-a/*",
        "arn:aws:s3:::bucket-b/*"
      ],
      "Sid": ""
    }
  ]
}
EOF

cat > minio_user.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject"        
      ],
      "Effect": "Allow",
      "Resource": [
        "arn:aws:s3:::bucket-a/*"
      ],
      "Sid": ""
    }
  ]
}
EOF
```

Add canned policies. 

```bash
mc admin policy add minio minioSuperuser minio_superuser.json
mc admin policy add minio minioUser minio_user.json
```

The names `minioSuperuser` and `minioUser` can now be referenced 
via JWT claim attribute `policy`.
