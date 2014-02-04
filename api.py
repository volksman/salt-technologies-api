# import httplib, urllib
# from urlparse import urlparse, parse_qsl

# # connection parameters to the Admeris IOP gateway
# URL = 'https://test.admeris.com/store/checkout/iopproxy.jsp'
# parms = {
#     'merchantId':  '50641',
#     'storeId': '12155',
#     'apiToken': 'q0rmRTSTuYwmNjbV'
#     }

# def verify(tid):
#     url = urlparse(URL)
#     conn = httplib.HTTPSConnection(url[1])
#     parms.update({'transactionId': tid, "txnType": "Verify"})
#     conn.request("POST", url[2], urllib.urlencode(parms),
#                  {"Content-type": "application/x-www-form-urlencoded"})

#     return dict(parse_qsl(conn.getresponse().read()))

import logging
import requests
import time
import sys

logger = logging.getLogger('salt_log')
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
    'C112_PERIODIC_PURCHASE_COMPLETE_OR_CANCELLED': PeriodicPurchaseCompleteOrCancelled,
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

class Salt(object):
    def __init__(self, apikey=None, merchant_id=None, url=None, debug=False):
        """ initialize the API client

        Args:
            apikey (str): provide your Salt API key, required
            merchant_id (str): provide your Salt Merchat ID, required
            debug (bool): set True to log to "salt_log" logger at INFO level
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
        if url is None and ROOT is None: raise Error('You must provide a Salt API root endpoint')

        if url is not None:
            ROOT = url

        self.credit_card_verification = CreditCardVerification(self)

    def call(self, params=None):
        """ Actually make the API call with the given params - this should only
        be called by the namespace methods - use the helpers in regular usage
        like m.helper.ping()
        """

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

        if response.status_code != requests.codes.ok or response_body['ERROR_MESSAGE'] != 'SUCCESS':
            raise self.cast_error(response_body)
        return response_body

    def cast_error(self, result):
        """ Take a result representing an error and cast it to a specific
        exception if possible (use a generic Error exception for unknown cases)
        """

        if result['ERROR_MESSAGE'] in ERROR_MAP:
           return ERROR_MAP[result['ERROR_MESSAGE']](result['DEBUG_MESSAGE'])
        return Error(result['DEBUG_MESSAGE'])

    def log(self, *args, **kwargs):
        '''Proxy access to the mailchimp logger, changing the level based on the debug setting'''
        logger.log(self.level, *args, **kwargs)

    def __repr__(self):
        return '<SaltAPI %s - %s>' % (self.apikey, self.merchant_id)

class CreditCardVerification(object):
    """ Verify a CC number """

    def __init__(self, master):
        self.master = master

    def verify(self, credit_card_number, expiry_date, zipcode, street, **kwargs):
        """ This call will validate a CC.

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

        return self.master.call(_params)
