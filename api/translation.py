import copy
import re
from loguru import logger

class MoroccanTranslator:
    """
    Middleware agent to translate financial domain data between Moroccan 
    and Bangladeshi contexts (for use with the original Bangladeshi dataset model).
    """
    
    CONVERSION_RATE = 13.07
    
    CITIES_MAPPING = {
        "casablanca": "Dhaka",
        "rabat": "Chittagong",
        "marrakech": "Sylhet",
        "fès": "Rajshahi",
        "fes": "Rajshahi",
        "tanger": "Khulna",
        "agadir": "Comilla",
        "meknès": "Mymensingh",
        "meknes": "Mymensingh",
        "oujda": "Rangpur"
    }

    COUNTRIES_MAPPING = {
        "maroc": "Bangladesh",
        "algérie": "India",
        "algerie": "India",
        "france": "India",
    }
    
    PAYMENT_MAPPING = {
        "carte bancaire": "card",
        "carte": "card",
        "visa": "card",
        "mastercard": "card",
        "cih": "card",
        "attijari": "card",
        "cmi": "card",
        "virement": "bank_transfer",
        "espèces": "cash",
        "especes": "cash",
        "orange money": "bkash",
        "inwi money": "bkash",
        "wafacash": "nagad",
    }
    
    @classmethod
    def get_payment_mapping(cls, pm: str) -> str:
        if not pm:
            return "card"
        pm_lower = pm.lower().strip()
        for key, value in cls.PAYMENT_MAPPING.items():
            if key in pm_lower:
                return value
        if "mobile" in pm_lower or "money" in pm_lower:
            return "rocket"
        return "card"
        
    @classmethod
    def get_city_mapping(cls, city: str) -> str:
        if not city:
            return "Dhaka"
        city_lower = city.lower().strip()
        return cls.CITIES_MAPPING.get(city_lower, "Dhaka")
        
    @classmethod
    def get_country_mapping(cls, country: str) -> str:
        if not country:
            return "Bangladesh"
        country_lower = country.lower().strip()
        return cls.COUNTRIES_MAPPING.get(country_lower, "Bangladesh")

    @classmethod
    def translate_to_bangladesh(cls, transaction: dict) -> tuple[dict, dict]:
        """
        Adapts a Moroccan transaction to Bangladeshi space.
        Returns the adapted transaction and a context dict for reverse translation.
        """
        context = {
            "city": transaction.get("city", ""),
            "country": transaction.get("country", ""),
            "currency": transaction.get("currency", "")
        }
        tx = copy.deepcopy(transaction)
        
        tx["city"] = cls.get_city_mapping(tx.get("city", ""))
        tx["country"] = cls.get_country_mapping(tx.get("country", ""))
        tx["payment_method"] = cls.get_payment_mapping(tx.get("payment_method", ""))
        tx["currency"] = "BDT"
        
        if tx.get("transaction_amount") is not None:
            tx["transaction_amount"] = float(tx["transaction_amount"]) * cls.CONVERSION_RATE
            tx["fee_amount"] = tx["transaction_amount"] * 0.02
        else:
            tx["transaction_amount"] = 1500.0
            tx["fee_amount"] = tx["transaction_amount"] * 0.02
            
        if tx.get("txn_sum_24h") is not None:
            tx["txn_sum_24h"] = float(tx["txn_sum_24h"]) * cls.CONVERSION_RATE
            
        if tx.get("avg_amount_30d") is not None:
            tx["avg_amount_30d"] = float(tx["avg_amount_30d"]) * cls.CONVERSION_RATE

        logger.debug(f"[MIDDLEWARE] ORIGINAL JSON (Maroc): {transaction}")
        logger.debug(f"[MIDDLEWARE] ADAPTED JSON (Bangladesh): {tx}")
            
        return tx, context

    @classmethod
    def translate_explanation_to_maroc(cls, explanation: str, context: dict) -> str:
        """
        Reverts the generated explanation back to the Moroccan context.
        """
        res = explanation
        target_currency = context.get("currency", "MAD")
        if not target_currency or target_currency.upper() == "BDT":
            target_currency = "MAD"
            
        def _replace_amount(match):
            amount_str = match.group(1).replace(',', '')
            try:
                amount_bdt = float(amount_str)
                amount_mad = amount_bdt / cls.CONVERSION_RATE
                if amount_mad.is_integer():
                    return f"{int(amount_mad)} {target_currency}"
                else:
                    return f"{amount_mad:.2f} {target_currency}"
            except ValueError:
                return match.group(0)
            
        res = re.sub(r'(\d+(?:[.,]\d+)?)\s*BDT', _replace_amount, res, flags=re.IGNORECASE)
        res = re.sub(r'\bBDT\b', target_currency, res, flags=re.IGNORECASE)
        
        bangla_city = cls.get_city_mapping(context.get("city", ""))
        original_city = context.get("city")
        if original_city and original_city.lower() != bangla_city.lower():
            if bangla_city:
                res = re.sub(rf'\b{bangla_city}\b', original_city, res, flags=re.IGNORECASE)
                
        bangla_country = cls.get_country_mapping(context.get("country", ""))
        original_country = context.get("country")
        if original_country and original_country.lower() != bangla_country.lower():
            if bangla_country:
                res = re.sub(rf'\b{bangla_country}\b', original_country, res, flags=re.IGNORECASE)
                
        res = re.sub(r'\bBangladesh\b', 'Maroc', res, flags=re.IGNORECASE)
        res = re.sub(r'\bDhaka\b', 'Casablanca', res, flags=re.IGNORECASE)
        
        return res
