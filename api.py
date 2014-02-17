import logging
import requests
import time
import sys

logger = logging.getLogger('salt_api')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stderr))

VERSION = '0.0.1'

ROOT = 'https://test.salt.com/gateway/creditcard/processor.do'

class Error(Exception): pass
class TimedOut(Error): pass
class SaltSystemError(Error): pass
class NetworkError(Error): pass
class ValidationError(Error): pass
class Declined(Error): pass
class InvalidMerchantCredentials(Error): pass
class AmountOutOfBounds(Error): pass
class InvalidPurchase(Error): pass
class InvalidTransaction(Error): pass
class PurchaseNotInRefundableState(Error): pass
class PurchaseRefundAmountOverLimit(Error): pass
class TransactionNotVoidable(Error): pass
class RequestDenied(Error): pass
class OrderIdAlreadyExist(Error): pass
class InvalidTotalNumberInstallments(Error): pass
class TransactionExceedsAccountLimits(Error): pass
class TransactionDoesNotExist(Error): pass
class PeriodicPurchaseCompleteOrCancelled(Error): pass
class InvalidCreditCardNumber(Error): pass
class InvalidCreditCardExpiryDate(Error): pass
class InvalidCreditCardCVV2Format(Error): pass
class InvalidZipFormat(Error): pass
class InvalidStreetFormat(Error): pass
class CVV2VerificationFailed(Error): pass
class CVV2VerificationNotSupported(Error): pass
class AVSFailed(Error): pass
class AVSNotSupported(Error): pass
class CreditCardExpired(Error): pass
class CardNotSupported(Error): pass
class CardLimitExceeded(Error): pass
class CardLostOrStolen(Error): pass
class StorageTokenIdAlreadyInUse(Error): pass
class StorageRecordDoesNotExist(Error): pass
class NoCreditCardInStorageRecord(Error): pass
class DeclinedFromFraudProvider(Error): pass
class ApprovedFromFraudProvider(Error): pass
class ReviewFromFraudProvider(Error): pass

ERROR_MAP = {
    'C001_TIMED_OUT': TimedOut,
    'C002_SYSTEM_ERROR': SaltSystemError,
    'C003_NETWORK_ERROR': NetworkError,
    'C004_VALIDATION_ERROR': ValidationError,
    'C005_DECLINED': Declined,
    'C100_INVALID_MERCHANT_CREDENTIALS': InvalidMerchantCredentials,
    'C101_AMOUNT_OUT_OF_BOUNDS': AmountOutOfBounds,
    'C102_INVALID_PURCHASE': InvalidPurchase,
    'C103_INVALID_TRANSACTION': InvalidTransaction,
    'C104_PURCHASE_NOT_IN_REFUNDABLE_STATE': PurchaseNotInRefundableState,
    'C105_PURCHASE_REFUND_AMOUNT_OVER_LIMIT': PurchaseRefundAmountOverLimit,
    'C106_TRANSACTION_NOT_VOIDABLE': TransactionNotVoidable,
    'C107_REQUEST_DENIED': RequestDenied,
    'C108_ORDER_ID_ALREADY_EXIST': OrderIdAlreadyExist,
    'C109_INVALID_TOTAL_NUMBER_INSTALLMENTS': InvalidTotalNumberInstallments,
    'C110_TRANSACTION_EXCEEDS_ACCOUNT_LIMITS': TransactionExceedsAccountLimits,
    'C111_TRANSACTION_DOES_NOT_EXIST': TransactionDoesNotExist,
    'C112_PERIODIC_PURCHASE_COMPLETE_OR_CANCELLED':
        PeriodicPurchaseCompleteOrCancelled,
    'C200_INVALID_CREDIT_CARD_NUMBER': InvalidCreditCardNumber,
    'C201_INVALID_CREDIT_CARD_EXPIRY_DATE': InvalidCreditCardExpiryDate,
    'C202_INVALID_CREDIT_CARD_CVV2_FORMAT': InvalidCreditCardCVV2Format,
    'C203_INVALID_ZIP_FORMAT': InvalidZipFormat,
    'C204_INVALID_STREET_FORMAT': InvalidStreetFormat,
    'C220_CVV2_VERIFICATION_FAILED': CVV2VerificationFailed,
    'C221_CVV2_VERIFICATION_NOT_SUPPORTED': CVV2VerificationNotSupported,
    'C222_AVS_FAILED': AVSFailed,
    'C223_AVS_NOT_SUPPORTED': AVSNotSupported,
    'C224_CREDIT_CARD_EXPIRED': CreditCardExpired,
    'C225_CARD_NOT_SUPPORTED': CardNotSupported,
    'C226_CARD_LIMIT_EXCEEDED': CardLimitExceeded,
    'C227_CARD_LOST_OR_STOLEN': CardLostOrStolen,
    'C300_STORAGE_TOKEN_ID_ALREADY_IN_USE': StorageTokenIdAlreadyInUse,
    'C301_STORAGE_RECORD_DOES_NOT_EXIST': StorageRecordDoesNotExist,
    'C302_NO_CREDIT_CARD_IN_STORAGE_RECORD': NoCreditCardInStorageRecord,
    'C400_DECLINED_FROM_FRAUD_PROVIDER': DeclinedFromFraudProvider,
    'C401_APPROVED_FROM_FRAUD_PROVIDER': ApprovedFromFraudProvider,
    'C402_REVIEW_FROM_FRAUD_PROVIDER': ReviewFromFraudProvider,
}

def _get_cc_or_id(kwargs):
    credit_card_number = kwargs.get('credit_card_number', None)
    expiry_date = kwargs.get('expiry_date', None)
    storage_token_id = kwargs.get('storage_token_id', None)

    if credit_card_number and expiry_date and storage_token_id:
        raise Error('Only provide CC and Exp OR StorageID not both')

    if not storage_token_id and not credit_card_number and not expiry_date:
        raise Error('Need to provide a CC and Exp or StorageID')

    if storage_token_id:
        return { 'storageTokenId': storage_token_id }
    else:
        return {
            'creditCardNumber': credit_card_number,
            'expiry_date': expiry_date
        }
    raise Error('No CC or Storage info found')

class Salt(object):
    def __init__(self, apikey=None, merchant_id=None, url=None, debug=False):
        """ initialize the API client

        Args:
            apikey (str): provide your Salt API key, required
            merchant_id (str): provide your Salt Merchat ID, required
            debug (bool): set True to log to "salt_api" logger at INFO level
        """

        self.session = requests.session()
        self.last_request = None

        if debug:
            self.level = logging.INFO
        else:
            self.level = logging.DEBUG

        if apikey is None: raise Error('You must provide a Salt API key')
        if merchant_id is None: raise Error('You must provide a Merchant ID')

        self.apikey = apikey
        self.merchant_id = merchant_id

        global ROOT
        if url is None and ROOT is None:
            raise Error('You must provide a Salt API root endpoint')

        if url is not None:
            ROOT = url

        self.recuring_purchase = RecurringPurchase(self)
        self.secure_storage = SecureStorage(self)

    def call(self, params=None):
        """ Actually make the API call with the given params """

        if params is None: params = {}

        params['apiToken'] = self.apikey
        params['merchantId'] = self.merchant_id

        self.log('POST to %s: %s' % (ROOT, params))
        start = time.time()
        response = self.session.post(
            ROOT,
            data=params,
            headers={'user-agent': 'SaltTechnologiesAPI-Python/%s' % VERSION})
        try:
            # grab the remote_addr before grabbing the text since the socket
            # will go away
            remote_addr = response.raw._original_response.fp._sock.getpeername()
        except:
            # we use two private fields when getting the remote_addr,
            # so be a little robust against errors
            remote_addr = (None, None)

        response_body = {}
        response_attrs = response.text.split('\n')
        for attr in response_attrs[:-1]:
            key, value = attr.split('=')
            if value == 'true':
                value = True
            elif value == 'false':
                value = False
            response_body[key] = value

        complete_time = time.time() - start
        self.log('Received %s in %.2fms: %s' % (
            response.status_code, complete_time * 1000, response.text))
        self.last_request = {
            'request_body': params,
            'response_body': response.text,
            'remote_addr': remote_addr,
            'response': response,
            'time': complete_time
        }

        if response.status_code != requests.codes.ok or \
            response_body['ERROR_MESSAGE'] != 'SUCCESS':
                raise self.cast_error(response_body)
        return response_body

    def cast_error(self, result):
        """ Take a result representing an error and cast it to a specific
        exception if possible (use a generic Error exception for unknown cases)
        """

        if result['ERROR_MESSAGE'] in ERROR_MAP:
            return ERROR_MAP[result['ERROR_MESSAGE']](result['ERROR_MESSAGE'])
        return Error(result['ERROR_MESSAGE'])

    def log(self, *args, **kwargs):
        """ Proxy access to the salt_api logger, changing the level based on the
        debug setting
        """
        logger.log(self.level, *args, **kwargs)

    def __repr__(self):
        return '<SaltAPI %s - %s>' % (self.apikey, self.merchant_id)

    # Simple single function wrappers
    def single_purchase(self, amount, order_id, *args, **kwargs):
        """ The singlePurchase method runs a one-time charge against a credit
        card.

        Args:
            amount (dec): amount to be charged

            Either:
            credit_card_number (int)
            expiry_date (int)

            OR:
            storage_token_id (int)

        Optional Args:
            cvv (int)
            order_id (str)
            market_segment_code (str): defaults to I
            avs_request_code (int): defaults to 0
            cvv2_request_code (int): defaults to 0

        """
        _params = {
            'requestCode': 'singlePurchase',
            'amount': amount,
            'orderId': order_id
        }

        cc_meta = _get_cc_or_id(kwargs)

        _params['zip'] = kwargs.get('zip', '')
        _params['street'] = kwargs.get('street', '')
        _params['marketSegmentCode'] = kwargs.get('market_segment_code', 'I')
        _params['avsRequestCode'] = kwargs.get('avs_request_code', 0)
        _params['cvv2RequestCode'] = kwargs.get('cvv2_request_code', 0)

        _params = dict(_params.items() + cc_meta.items())

        self.cvv = kwargs.get('cvv', None)
        if self.cvv:
            _params['cvv'] = self.cvv

        return self.call(_params)

    def void(self, transaction_id, transaction_order_id, **kwargs):
        """ Cancels a transaction, preventing it from being settled. A Void can
        only be performed on a transaction belonging to the current batch,
        before the current batch is closed (i.e. before the end of day).

        Args:
            transaction_id (int)
            transaction_order_id (str)

        Optional Args:
            market_segment_code (str): defaults to I

        """

        _params = {
            'requestCode': 'void',
            'transactionId': transaction_id,
            'transaction_order_id': transaction_order_id,
        }
        _params['marketSegmentCode'] = kwargs.get('market_segment_code', 'I')

        return self.call(_params)

    def refund(self, transaction_id, transaction_order_id, order_id, amount,
        **kwargs):
        """ Returns funds from a previously settled purchase to the customer.
        Refunds can only be performed on a purchase that is part of an
        already-closed batch.

        Args:
            transaction_id (int)
            transaction_order_id (str)
            order_id (str)
            amount (int)

        Optional Args:
            market_segment_code (str): defaults to I

        """

        _params = {
            'requestCode': 'refund',
            'transactionId': transaction_id,
            'transactionOrderId': transaction_order_id,
            'orderId': order_id,
            'amount': amount
        }
        _params['marketSegmentCode'] = kwargs.get('market_segment_code', 'I')

        return self.call(_params)

    def transaction_verification(self, transaction_id, **kwargs):
        """ In certain cases when you are unsure of the results of the
        transaction, such as when a transaction times out, you may need to
        double-check its status.

        Args:
            transaction_id (int)

        Optional Args:
            market_segment_code (str): defaults to I

        """

        _params = {
            'requestCode': 'verifyTransaction',
            'transactionId': transaction_id
        }
        _params['marketSegmentCode'] = kwargs.get('market_segment_code', 'I')

        return self.call(_params)

    def credit_card_verification(self, credit_card_number, expiry_date, zipcode,
        street, **kwargs):
        """ Use a verifyCreditCard request to check the status of a credit card.
        The returned receipt will contain information about the card's validity,
        Secure Storage information if the card uses Secure Storage and Fraud
        information if the card uses the Advanced Fraud Suite.

        Args:
            credit_card_number (int): a credit card PAN
            expiry_date (int): YYMM of expiry
            zipcode (str): K1K1K1 or 90210
            street (str): street address for CC

        Optional Args:
            cvv (int): no default
            market_segment_code (str): defaults to I
            avs_request_code (int): defaults to 0
            cvv2_request_code (int): defaults to 0

        """

        _params = {
            'requestCode': 'verifyCreditCard',
            'creditCardNumber': credit_card_number,
            'expiryDate': expiry_date,
            'zip': zipcode,
            'street': street,
        }
        _params['marketSegmentCode'] = kwargs.get('market_segment_code', 'I')
        _params['avsRequestCode'] = kwargs.get('avs_request_code', 0)
        _params['cvv2RequestCode'] = kwargs.get('cvv2_request_code', 0)
        self.cvv = kwargs.get('cvv', None)
        if self.cvv:
            _params['cvv'] = self.cvv

        return self.call(_params)

    def batch_closure(self, **kwargs):
        """ All batches are closed automatically every night at 12:00 am EST.
        If for some reason you want to close a batch manually during the day,
        this may be done with a batch request. Note that this will NOT prevent
        the automatic daily batch closure.

        Optional Args:
            market_segment_code (str): defaults to I

        """

        _params = {
            'requestCode': 'batch',
            'operationCode': 'close'
        }
        _params['marketSegmentCode'] = kwargs.get('market_segment_code', 'I')

        return self.call(_params)

    def fraud(self, transaction_id, fraud_session_id, auth, **kwargs):
        """ Allow merchants to update fraud AUTH status if they use other
        payment processing service.

        Args:
            transaction_id (int)
            fraud_session_id (int)
            auth (int)

        Optional Args:
            market_segment_code (str): defaults to I

        """

        _params = {
            'requestCode': 'fraudUpdate',
            'transactionId': transaction_id,
            'fraudSessionId': fraud_session_id,
            'auth': auth
        }
        _params['marketSegmentCode'] = kwargs.get('market_segment_code', 'I')

        return self.call(_params)

class SecureStorage(object):
    """ With the Secure Storage API, merchants can remotely store credit card
    and other sensitive customer data with SALT to increase security and reduce
    the scope of PCI Compliance.

    When information is stored with SALT, a 'Storage Token' (which identifies
    the information in secure storage) is returned in response. This Storage
    Token can be used for all subsequent transactions including purchases and
    credit card verification.
    """

    def __init__(self, master):
        self.master = master

    def _get_params(self, action, storage_token_id, credit_card_number, expiry_date,
        kwargs):
        _params = {
            'requestCode': 'secureStorage',
            'operationCode': action,
            'storageTokenId': storage_token_id,
            'creditCardNumber': credit_card_number,
            'expiryDate': expiry_date,
        }

        if 'profile_first_name' in kwargs:
            _params['profileFirstName'] = kwargs['profile_first_name']

        if 'profile_last_name' in kwargs:
            _params['profileLastName'] = kwargs['profile_last_name']

        if 'profile_phone_number' in kwargs:
            _params['profilePhoneNumber'] = kwargs['profile_phone_number']

        if 'profile_address' in kwargs:
            _params['profileAddress1'] = kwargs['profile_address']

        if 'profile_postal' in kwargs:
            _params['profilePostal'] = kwargs['profile_postal']

        if 'profile_city' in kwargs:
            _params['profileCity'] = kwargs['profile_city']

        if 'profile_country' in kwargs:
            _params['profileCoutry'] = kwargs['profile_country']

        _params['marketSegmentCode'] = kwargs.get('market_segment_code', 'I')

        return _params

    def create(self, storage_token_id, credit_card_number, expiry_date,
        **kwargs):
        """ Create a storage profile

        Args:
            storage_token_id (str)
            credit_card_number (int)
            expiry_date (int)

        Optional Args:
            market_segment_code (str): defaults to I
            profile_first_name (str)
            profile_last_name (str)
            profile_phone_number (str)
            profile_address (str)
            profile_postal (str)
            profile_city (str)
            profile_country (str)

        """
        _params = self._get_params('create', storage_token_id,
            credit_card_number, expiry_date, kwargs)

        return self.master.call(_params)

    def update(self, storage_token_id, credit_card_number, expiry_date, *args,
        **kwargs):

        """ Update a storage profile """
        _params = self._get_params('update', storage_token_id, credit_card_number, expiry_date,
            kwargs)
        return self.master.call(_params)

    def delete(self, storage_token_id, *args, **kwargs):
        """ Delete a storage profile """
        _params = {
            'requestCode': 'secureStorage',
            'operationCode': 'delete',
            'storageTokenId': storage_token_id,
        }

        _params['marketSegmentCode'] = kwargs.get('market_segment_code', 'I')

        return self.master.call(_params)

    def query(self, storage_token_id, *args, **kwargs):
        _params = {
            'requestCode': 'secureStorage',
            'operationCode': 'query',
            'storageTokenId': storage_token_id,
        }

        _params['marketSegmentCode'] = kwargs.get('market_segment_code', 'I')

        return self.master.call(_params)

class RecurringPurchase(object):
    """ You can use SALT's Recurring Payment feature when the customer is
    billed periodically, or when splitting payment into a number of
    separate payments.
    """

    def __init__(self, master):
        self.master = master

    def _create_update_params(amount, periodic_purchase_state_code,
        periodic_purchase_schedule_type_code, periodic_purchase_interval_length,
        order_id, start_date, end_date, next_payment_date,
        credit_card_number, expiry_date, kws):

        _params = {
            'requestCode': 'recurringPurchase',
            'operationCode': 'create',
            'amount': amount,
            'periodicPurchaseStateCode': periodic_purchase_state_code,
            'periodicPurchaseScheduleTypeCode':
                periodic_purchase_schedule_type_code,
            'periodicPurchaseIntervalLength': periodic_purchase_interval_length,
            'orderId': order_id,
            'startDate': start_date,
            'endDate': end_date,
            'nextPaymentDate': next_payment_date,
        }

        _params['customerId'] = kws.get('customer_id', '')
        _params['marketSegmentCode'] = kws.get('market_segment_code', 'I')
        _params['avsRequestCode'] = kws.get('avs_request_code', 0)
        _params['cvv2RequestCode'] = kws.get('cvv2_request_code', 0)

        cc_meta = _get_cc_or_id(kws)
        _params = dict(_params.items() + cc_meta.items())

        return _params

    def create(self, amount, periodic_purchase_state_code,
        periodic_purchase_schedule_type_code, periodic_purchase_interval_length,
        order_id, start_date, end_date, next_payment_date,
        credit_card_number, expiry_date, **kwargs):

        _params = self._create_update_params(amount,
            periodic_purchase_state_code, periodic_purchase_schedule_type_code,
            periodic_purchase_interval_length, order_id, start_date, end_date,
            next_payment_date, credit_card_number, expiry_date, kwargs)

        _params['operationCode'] = 'create'

        return self.master.call(_params)

    def update(self, amount, periodic_purchase_state_code,
        periodic_purchase_schedule_type_code, periodic_purchase_interval_length,
        order_id, start_date, end_date, next_payment_date,
        credit_card_number, expiry_date, **kwargs):

        _params = self._create_update_params(amount,
            periodic_purchase_state_code, periodic_purchase_schedule_type_code,
            periodic_purchase_interval_length, order_id, start_date, end_date,
            next_payment_date, credit_card_number, expiry_date, kwargs)

        _params['operationCode'] = 'update'

        return self.master.call(_params)

    def execute(self, order_id, cvv, **kwargs):
        _params = {
            'requestCode': 'recurringPurchase',
            'operationCode': 'execute',
            'orderId': order_id,
            'cvv2': cvv
        }

        _params['marketSegmentCode'] = kwargs.get('market_segment_code', 'I')

        return self.master.call(_params)

    def hold(self, order_id, **kwargs):
        _params = {
            'requestCode': 'recurringPurchase',
            'operationCode': 'update',
            'orderId': order_id,
            'periodicPurchaseStateCode': 3
        }

        _params['marketSegmentCode'] = kwargs.get('market_segment_code', 'I')

        return self.master.call(_params)

    def resume(self, order_id, **kwargs):
        _params = {
            'requestCode': 'recurringPurchase',
            'operationCode': 'update',
            'orderId': order_id,
            'periodicPurchaseStateCode': 1
        }

        _params['marketSegmentCode'] = kwargs.get('market_segment_code', 'I')

        return self.master.call(_params)

    def cancel(self, order_id, **kwargs):
        _params = {
            'requestCode': 'recurringPurchase',
            'operationCode': 'update',
            'orderId': order_id,
            'periodicPurchaseStateCode': 4
        }

        _params['marketSegmentCode'] = kwargs.get('market_segment_code', 'I')

        return self.master.call(_params)
