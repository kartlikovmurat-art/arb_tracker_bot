from enum import Enum


class TradeType(str, Enum):
    CEX_CEX = "CEX_CEX"
    CEX_DEX = "CEX_DEX"
    DEX_CEX = "DEX_CEX"
    DEX_DEX = "DEX_DEX"