# Web App for ABA Services
I have built this app to help my family member's small business where they provide ABA services to the special needs clients.\
This Web Application is built to assist the business to manage client records, employee records, session records and invoicing.

## During container image build and container deployment

### Environment Variables
Following are the environment variables 
```
ORG_NAME=""
ORG_ADDRESS=""
ORG_PHONE=""
ORG_EMAIL=""
```
These variables will be used to generate the Invoice.\
Also, ORG_NAME is used as the Brand Name in the side navigation bar in the webapp. 

### Persistent volume for DB
DB is stored in /app/data, so you can have a persistent volume created to store the DB.\
Currently DB is SQLite only.


## After initializing the Web Application
Web Application initialized with the default super user which is:\
`username: admin@example.com`\
`password: Admin1!`

**Note:** Change the password immediately after the initial deployment.

### What admin@example.com user can do?
Super user can only create other users who can access the webapp.\
Additionally, super user can add entries to the Designation and Activity table, to start the process for onboarding employees and add session information.\
<img width="247" height="361" alt="image" src="https://github.com/user-attachments/assets/ae91b198-2e84-4459-afee-38557eacbe71" />

**There are two types of users:**

- **admin** - One admin user should be created who should be able to do the same actions like the super user and additionally, can manage employee, client and session records.\
  Admin should be able to generate the invoices too.
  They are basically organization admins.\
  <img width="235" height="549" alt="image" src="https://github.com/user-attachments/assets/16d9324c-8fce-4e71-955c-acd195fa7471" />

- **user** - Normal user will only have access to manage session records for themselves and the access to the parts of webapp is limited.\
  <img width="233" height="270" alt="image" src="https://github.com/user-attachments/assets/9aef0006-8b71-43a9-b534-cd053a3f8397" />

## Starting to use the Web Application
1) To begin with there should be at least one **Behaviour Aanalyst** as each client will need one.
2) Then a new Client can be onboarded. While adding the client you'll be asked to enter the rate for Supervision and Therapy.\
   Activities will have to be categorized under one of these, so that the invoice will be based on the activity vategory and the rate associated with it.
3) Then you can add the sessions taken for the client. Normal user will only be able to Create, Read, Update and Delete sessions for themselves but not for other's. Admin should be able to carry out those on behalf of other's.
4) Admin can generate invoice by selecting the client and date range to pick all the session which meets that criteria.
5) Once the invoice is generated, it can be downloaded in PDF format to share with the client.\
   <img width="227" height="97" alt="image" src="https://github.com/user-attachments/assets/84ea0092-d200-4ddd-9156-e643d9e26f11" />
6) Mark the invoice as sent once done.\
   <img width="227" height="96" alt="image" src="https://github.com/user-attachments/assets/3aed1d78-0ea2-426c-87d3-d0f32a3d3a15" />
7) Once the invoice is shared with the client, it cannot be deleted unless sent back to draft.\
   <img width="233" height="86" alt="image" src="https://github.com/user-attachments/assets/d981629c-3193-4ce6-894d-69773ace6c36" />
8) Once payment is recieved, mark the invoice as paid.\
   <img width="233" height="86" alt="image" src="https://github.com/user-attachments/assets/bc52c1f2-1c9e-4373-8dc0-c42dd86f6dd7" />
9) You can download the invoice and the PDF should have the status changed from pending to paid.\
   <img width="231" height="84" alt="image" src="https://github.com/user-attachments/assets/a3d66b99-9d79-45c9-b660-67c5c33e548f" /><img width="231" height="99" alt="image" src="https://github.com/user-attachments/assets/41f00c22-80ec-4298-bf13-c0ccc9f3285d" />



