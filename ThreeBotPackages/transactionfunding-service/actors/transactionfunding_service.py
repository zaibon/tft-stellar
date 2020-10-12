import os
import sys
import random
import time
import stellar_sdk

from jumpscale.loader import j
from jumpscale.servers.gedis.baseactor import BaseActor, actor_method

current_full_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_full_path + "/sals/")
from transactionfunding_sal import ASSET_ISSUERS, WALLET_NAME, NUMBER_OF_SLAVES, fund_if_needed


_HORIZON_NETWORKS = {"TEST": "https://horizon-testnet.stellar.org", "STD": "https://horizon.stellar.org"}


class Transactionfunding_service(BaseActor):
    def _get_horizon_server(self, network):

        return stellar_sdk.Server(horizon_url=_HORIZON_NETWORKS[str(network)])

    def _create_fee_payment(self, from_address, asset):
        main_wallet = j.clients.stellar.get(WALLET_NAME)
        fee_target = main_wallet.address

        return stellar_sdk.Payment(fee_target, asset, "0.1", from_address)

    def _get_slave_fundingwallet_(self):
        earliest_sequence = int(time.time()) - 60  # 1 minute
        least_recently_used_wallet = None
        # Loop over the slavewallets, starting at a random one
        startindex = random.randrange(0, NUMBER_OF_SLAVES)
        r = range(startindex, startindex + NUMBER_OF_SLAVES)
        for slaveindex in [i % NUMBER_OF_SLAVES for i in r]:
            walletname = WALLET_NAME + "_" + str(slaveindex)
            wallet = j.clients.stellar.get(walletname)
            a = wallet.load_account()
            if a.last_created_sequence_is_used:
                return wallet
            else:
                if wallet.sequencedate < earliest_sequence:
                    earliest_sequence = wallet.sequencedate
                    least_recently_used_wallet = wallet
        return least_recently_used_wallet

    @actor_method
    def fund_transaction(self, transaction):
        """
        param:transaction = (S)
        return: transaction_xdr = (S)
        ```
        """
        funding_wallet = self._get_slave_fundingwallet_()
        if not funding_wallet:
            raise j.exceptions.Base("Service Unavailable")

        # after getting the wallet, the required imports are available

        if str(funding_wallet.network) == "TEST":
            network_passphrase = stellar_sdk.Network.TESTNET_NETWORK_PASSPHRASE
        else:
            network_passphrase = stellar_sdk.Network.PUBLIC_NETWORK_PASSPHRASE
        txe = stellar_sdk.transaction_envelope.TransactionEnvelope.from_xdr(transaction, network_passphrase)

        source_public_kp = stellar_sdk.Keypair.from_public_key(funding_wallet.address)
        source_signing_kp = stellar_sdk.Keypair.from_secret(funding_wallet.secret)

        if len(txe.transaction.operations) == 0:
            raise j.exceptions.NotFound("No operations in the supplied transaction")
        asset = None
        for op in txe.transaction.operations:
            if type(op) != stellar_sdk.operation.Payment:
                raise j.exceptions.Value("Only payment operations are supported")
            if op.asset.code not in ASSET_ISSUERS:
                raise j.exceptions.Value("Unsupported asset")
            if ASSET_ISSUERS[op.asset.code][str(funding_wallet.network)] != op.asset.issuer:
                raise j.exceptions.Value("Unsupported asset")
            if asset:
                if asset != op.asset:
                    raise j.exceptions.Value("Only 1 type of asset is supported")
            else:
                asset = op.asset

        txe.transaction.operations.append(self._create_fee_payment(txe.transaction.operations[0].source, asset))

        # set the necessary fee
        horizon_server = self._get_horizon_server(funding_wallet.network)
        base_fee = horizon_server.fetch_base_fee()
        txe.transaction.fee = base_fee * len(txe.transaction.operations)

        source_account = funding_wallet.load_account()
        source_account.increment_sequence_number()
        txe.transaction.source = source_public_kp

        txe.transaction.sequence = source_account.sequence
        txe.sign(source_signing_kp)

        transaction_xdr = txe.to_xdr()
        fund_if_needed(funding_wallet.name)
        return transaction_xdr


Actor = Transactionfunding_service
