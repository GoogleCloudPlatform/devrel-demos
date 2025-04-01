HOST="cymbalbank.cx6oakwa20qh.us-west-1.rds.amazonaws.com"
POSTGRES_DB="accounts-db"
POSTGRES_USER="postgres"
LOCAL_ROUTING_NUM="883745000"

add_user() {
    # Usage:  add_user "ACCOUNTID" "USERNAME" "FIRST_NAME"
    echo "adding user: $2"
    PGPASSWORD="Chiapet22!" psql -h $HOST -p 5432 -X -v ON_ERROR_STOP=1 -v account="$1" -v username="$2" -v firstname="$3" -v passhash="$DEFAULT_PASSHASH" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    INSERT INTO users VALUES (:'account', :'username', :'passhash', :'firstname', 'User', '2000-01-01', '-5', 'Bowling Green, New York City', 'NY', '10004', '111-22-3333') ON CONFLICT DO NOTHING;
EOSQL
}

add_external_account() {
    # Usage:  add_external_account "OWNER_USERNAME" "LABEL" "ACCOUNT" "ROUTING"
    echo "user $1 adding contact: $2"
    PGPASSWORD="Chiapet22!" psql -h $HOST -p 5432 -X -v ON_ERROR_STOP=1 -v username="$1" -v label="$2" -v account="$3" -v routing="$4" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    INSERT INTO contacts VALUES (:'username', :'label', :'account', :'routing', 'true') ON CONFLICT DO NOTHING;
EOSQL
}

add_contact() {
    # Usage:  add_contact "OWNER_USERNAME" "CONTACT_LABEL" "CONTACT_ACCOUNT"
    echo "user $1 adding external account: $2"
    PGPASSWORD="Chiapet22!" psql -h $HOST -p 5432 -X -v ON_ERROR_STOP=1 -v username="$1" -v label="$2" -v account="$3" -v routing="$LOCAL_ROUTING_NUM" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    INSERT INTO contacts VALUES (:'username', :'label', :'account', :'routing', 'false') ON CONFLICT DO NOTHING;
EOSQL
}

# Load test data into the database
create_accounts() {
    # Add demo users.
    add_user "1011226111" "testuser" "Test"
    add_user "1033623433" "alice" "Alice"
    add_user "1055757655" "bob" "Bob"
    add_user "1077441377" "eve" "Eve"

    # Make everyone contacts of each other
    add_contact "testuser" "Alice" "1033623433"
    add_contact "testuser" "Bob" "1055757655"
    add_contact "testuser" "Eve" "1077441377"
    add_contact "alice" "Testuser" "1011226111"
    add_contact "alice" "Bob" "1055757655"
    add_contact "alice" "Eve" "1077441377"
    add_contact "bob" "Testuser" "1011226111"
    add_contact "bob" "Alice" "1033623433"
    add_contact "bob" "Eve" "1077441377"
    add_contact "eve" "Testuser" "1011226111"
    add_contact "eve" "Alice" "1033623433"
    add_contact "eve" "Bob" "1055757655"

    # Add external accounts
    add_external_account "testuser" "External Bank" "9099791699" "808889588"
    add_external_account "alice" "External Bank" "9099791699" "808889588"
    add_external_account "bob" "External Bank" "9099791699" "808889588"
    add_external_account "eve" "External Bank" "9099791699" "808889588"
}

main() {
    # Check environment variables are set
    for env_var in ${ENV_VARS[@]}; do
        if [[ -z "${!env_var}" ]]; then
            echo "Error: environment variable '$env_var' not set. Aborting."
            exit 1
        fi
    done

    # A password hash + salt for the demo password 'bankofanthos'
    # Via Python3:  bcrypt.hashpw('bankofanthos'.encode('utf-8'), bcrypt.gensalt()).hex()
    DEFAULT_PASSHASH='\x2432622431322477595638423166664b50667a41524a6b69614d6c5075784847466961636b6d333349595952786d59645a6834435946696f49434943'

    create_accounts
}

main
