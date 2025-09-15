# My ABA App

## During container image build and container deployment

### Environment Variables

Following are the environment variables 
```
ORG_NAME=""
ORG_ADDRESS=""
ORG_PHONE=""
ORG_EMAIL=""
```
These variables will be used to generate the Invoice.
Also, ORG_NAME is used as the Brand Name in the Sidebar. 

### Persistent volume for DB

DB is stored in /app/data, so you can have a persisten volume created to store the DB.
Currently DB is SQLite only.


## After initializing the application

DB is initialized with the default admin/super user which is:\
`username: admin@example.com`\
`password: Admin1!`

**Note:** Change the password immediately after the initial deployment.


