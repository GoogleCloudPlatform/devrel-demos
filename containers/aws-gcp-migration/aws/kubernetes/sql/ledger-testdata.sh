#!/bin/bash

HOST="cymbalbank.cx6oakwa20qh.us-west-1.rds.amazonaws.com"
POSTGRES_DB="ledger-db"
POSTGRES_USER="postgres"
PG_PASSWORD="Chiapet22!"
LOCAL_ROUTING_NUM="883745000"

add_transaction() {
    DATE=$(date -j -f "%s" -u "$6" +"%Y-%m-%d %H:%M:%S UTC")
    echo "adding demo transaction: $1 -> $2"
    PGPASSWORD="Chiapet22!" psql -h $HOST -p 5432 -X -v ON_ERROR_STOP=1 -v fromacct="$1" -v toacct="$2" -v fromroute="$3" -v toroute="$4" -v amount="$5" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        INSERT INTO TRANSACTIONS (FROM_ACCT, TO_ACCT, FROM_ROUTE, TO_ROUTE, AMOUNT, TIMESTAMP)
        VALUES (:'fromacct', :'toacct', :'fromroute', :'toroute', :'amount', '$DATE');
EOSQL
}

create_transactions() {
    PAY_PERIODS=3
    DAYS_BETWEEN_PAY=14
    SECONDS_IN_PAY_PERIOD=$((86400 * $DAYS_BETWEEN_PAY))
    DEPOSIT_AMOUNT=250000

    # create a UNIX timestamp in seconds since the Epoch
    START_TIMESTAMP=$(($(date +%s) - $(($(($PAY_PERIODS + 1)) * $SECONDS_IN_PAY_PERIOD))))

    for i in $(seq 1 $PAY_PERIODS); do
        # create deposit transaction for each user
        for account in ${USER_ACCOUNTS[@]}; do
            add_transaction "$EXTERNAL_ACCOUNT" "$account" "$EXTERNAL_ROUTING" "$LOCAL_ROUTING_NUM" $DEPOSIT_AMOUNT $START_TIMESTAMP
        done

        # create 15-20 payments between users
        TRANSACTIONS_PER_PERIOD=$(shuf -i 15-20 -n1)
        for p in $(seq 1 $TRANSACTIONS_PER_PERIOD); do
            # randomly generate an amount between $10-$100
            AMOUNT=$(shuf -i 1000-10000 -n1)

            # randomly select a sender and receiver
            SENDER_ACCOUNT=${USER_ACCOUNTS[$RANDOM % ${#USER_ACCOUNTS[@]}]}
            RECIPIENT_ACCOUNT=${USER_ACCOUNTS[$RANDOM % ${#USER_ACCOUNTS[@]}]}
            # if sender equals receiver, send to a random anonymous account
            if [[ "$SENDER_ACCOUNT" == "$RECIPIENT_ACCOUNT" ]]; then
                RECIPIENT_ACCOUNT=$(shuf -i 1000000000-9999999999 -n1)
            fi

            TIMESTAMP=$(($START_TIMESTAMP + $(($SECONDS_IN_PAY_PERIOD * $p / $(($TRANSACTIONS_PER_PERIOD + 1))))))

            add_transaction "$SENDER_ACCOUNT" "$RECIPIENT_ACCOUNT" "$LOCAL_ROUTING_NUM" "$LOCAL_ROUTING_NUM" $AMOUNT $TIMESTAMP
        done

        START_TIMESTAMP=$(($START_TIMESTAMP + $(($i * $SECONDS_IN_PAY_PERIOD))))
    done
}

create_ledger() {
    # Account numbers for users 'testuser', 'alice', 'bob', and 'eve'.
    USER_ACCOUNTS=("1011226111" "1033623433" "1055757655" "1077441377")
    # Numbers for external account 'External Bank'
    EXTERNAL_ACCOUNT="9099791699"
    EXTERNAL_ROUTING="808889588"

    create_transactions
}

main() {
    # Check environment variables are set
    for env_var in ${ENV_VARS[@]}; do
        if [[ -z "${env_var}" ]]; then
            echo "Error: environment variable '$env_var' not set. Aborting."
            exit 1
        fi
    done

    create_ledger
}

main
