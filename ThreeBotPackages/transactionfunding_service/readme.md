# Transaction funding Service

A funding service accepts transaction envelopes and funds the required lumen as described in the [documentation](../../docs/transaction_funding.md).

To be used as a js-ng package.

## Requirements

You need following knowledge to start this server.

A funding wallet with trustlines to the tokens it funds payment transactions for.
It needs trustlines to all tokens it funds transactions for to claim the fee.

With a new funding wallet(Testnet):

```python
txfundingwallet = j.clients.stellar.new("txfundingwallet", network="TEST")
txfundingwallet.activate_through_friendbot()
txfundingwallet.add_trustline('TFT','GA47YZA3PKFUZMPLQ3B5F2E3CJIB57TGGU7SPCQT2WAEYKN766PWIMB3')
txfundingwallet.add_trustline('FreeTFT','GBLDUINEFYTF7XEE7YNWA3JQS4K2VD37YU7I2YAE7R5AHZDKQXSS2J6R')
txfundingwallet.save()
```

for production:

```python
txfundingwallet = j.clients.stellar.new("txfundingwallet", network="STD")
```

Activate it from another wallet

Add the trustlines:

```python
txfundingwallet.add_trustline('TFT','GBOVQKJYHXRR3DX6NOX2RRYFRCUMSADGDESTDNBDS6CDVLGVESRTAC47')
txfundingwallet.add_trustline('TFTA','GBUT4GP5GJ6B3XW5PXENHQA7TXJI5GOPW3NF4W3ZIW6OOO4ISY6WNLN2')
txfundingwallet.add_trustline('FreeTFT','GCBGS5TFE2BPPUVY55ZPEMWWGR6CLQ7T6P46SOFGHXEBJ34MSP6HVEUT')
txfundingwallet.save()

```

With an existing funding wallet:

`txfundingwallet_secret`: is the secret key of the funding account which holds the Lumens and already has the trustlines.

```python
j.clients.stellar.new("txfundingwallet", network="TEST",secret="<txfundingwallet_secret>")
txfundingwallet.save()

```

## Running

execute the following command in jsng shell:
`j.servers.threebot.start_default()`

Install the package.
Once this process is completed add the package to the threebot server from jsng shell like this:

```python
j.servers.threebot.default.packages.add(giturl="https://github.com/threefoldfoundation/tft-stellar/tree/master/ThreeBotPackages/transactionfunding_service")
```

The following kwargs can also be given to configure the package:

- `wallet`: the wallet used to fund the transactions, default: `txfundingwallet`
- `slaves`: the number of wallets to use to distribute the load, default: 30
- `secret`: Activation secret of wallet to import ( if you are not using an already existing wallet)
- `network`: "STD" or "TEST" to indicate the type of the stellar network (required when importing a wallet through the secret argument). Defaults to `None`. When set to "TEST" and no secret is given, a wallet on the Stellar testnet will be created and funded through friendbot.

If the wallet name does not exist and the secret or network are not set through the install arguments, environment variables can be used to set the secret and network:

- **TXFUNDING_WALLET_SECRET**
- **TFT_SERVICES_NETWORK**

The server will start at `<HOST>/transactionfunding_service/`

Test out the transfer tokens:

## Actors

There is one actor with 2 methods:

- `conditions` : get the conditions for funding transactions with XLM

  Example output:

  ```json
  [{"asset": "TFT:GA47YZA3PKFUZMPLQ3B5F2E3CJIB57TGGU7SPCQT2WAEYKN766PWIMB3", "fee_account_id": "GDREB646A2R7TLAF7WELQ6VAO7J5LBWTHYOBYIIPKX6PVYI7MSBFEKXZ", "fee_fixed": "0.01"}, {"asset": "TFTA:GB55A4RR4G2MIORJTQA4L6FENZU7K4W7ATGY6YOT2CW47M5SZYGYKSCT", "fee_account_id": "GDREB646A2R7TLAF7WELQ6VAO7J5LBWTHYOBYIIPKX6PVYI7MSBFEKXZ", "fee_fixed": "0.01"}]
  ```

- `fund_transaction`: Funds and signs a TFT transaction.
  - param `transaction`: Stellar transaction envelope in xdr

It can be called on the following url:`https://<host>//transactionfunding_service/actors/transactionfunding_service/fund_transaction`

There are two options of getting thetransaction funded:

- Send an unsigned transaction containg a single payment operation

The source of the transaction will be modified and a fee payment operation is added. It is signed by the transaction funding service and needs to be signed by the client and submitted to the Stellar network.

- Send a signed transaction containing the oiperation to execute and a fee payment operation. 

The details of the feepayment operation can be found through the conditions endpoint. Set the fee of your transaction to 0.
The transaction funding service will wrap the transaction in a feebump transaction and submit it to the Stellar network.

curl examle:

```sh
curl -v -k --insecure --header "Content-Type: application/json" --request POST --data '{"transaction":"AAAAAgAAAAAocv2DVEu84HDn4rR1dr/tUG6fhn0uwvzsugkRmtA1vwAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAQAAAAEAAAAAKHL9g1RLvOBw5+K0dXa/7VBun4Z9LsL87LoJEZrQNb8AAAABAAAAAMGcYGKdx+mthKbi831OYZSPxzT3/LgwV3dq4oeLvUETAAAAAVRGVAAAAAAAOfxkG3qLTLHrhsPS6JsSUB7+ZjU/J4oT1YBMKb/3n2QAAAAAAJiWgAAAAAAAAAAA"}' https://localhost:443/transactionfunding_service/actors/transactionfunding_service/fund_transaction
```

## Threefoldfoundation deployed urls

- Testnet: `https://testnet.threefold.io/threefoldfoundation/transactionfunding_service/fund_transaction`
- Production: `https://tokenservices.threefold.io/threefoldfoundation/transactionfunding_service/fund_transaction`

## Load distribution

In Stellar sequence numbers for an account must increase.
If only 1 account would be used, all request must essentially be executed in sequence and transmitted to the Stellar network before the next request to fund a transaction can be done.

Ths package creates extra slave wallets with the name of the basewallet appended with `_index`. It loops over the slaves to search for one where the last sequence is already accepted by the network and if not found, takes the slave that was least recently used, given that it was longer than a minute ago.
