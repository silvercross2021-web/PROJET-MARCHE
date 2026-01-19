"""
Exceptions personnalisées pour l'application market
"""


class MarketException(Exception):
    """Exception de base pour l'application market"""
    pass


class CommercantInactifException(MarketException):
    """Exception levée quand on essaie d'effectuer une action sur un commerçant inactif"""
    pass


class EtalDejaOccupeException(MarketException):
    """Exception levée quand on essaie d'attribuer un étal déjà occupé"""
    pass


class TicketDejaUtiliseException(MarketException):
    """Exception levée quand on essaie d'utiliser un ticket déjà utilisé"""
    pass


class MontantInvalideException(MarketException):
    """Exception levée quand un montant est invalide"""
    pass


class PaiementMensuelException(MarketException):
    """Exception levée lors d'erreurs avec les paiements mensuels"""
    pass


class ValidationException(MarketException):
    """Exception levée lors d'erreurs de validation"""
    pass

