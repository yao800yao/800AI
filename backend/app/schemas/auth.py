from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    account: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: "UserBrief"


class UserBrief(BaseModel):
    id: str
    business_id: str
    username: str
    email: str | None = None
    role: str
    avatar_url: str = ""
    credits: int = 0
    is_whitelisted: bool = False

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    promo_code: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: str
    verification_code: str
    verification_id: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    username: str


class RedeemCreditKeyRequest(BaseModel):
    key: str


class RedeemCreditKeyResponse(BaseModel):
    message: str
    credit_amount: int
    credits: int
    redeem_key: str
    used_at: datetime | None = None


class CreatePromoCodeRequest(BaseModel):
    platform_name: str


class UpdatePromoCodeRequest(BaseModel):
    platform_name: str


class PromoCodeItem(BaseModel):
    id: int
    code: str
    platform_name: str
    status: str
    created_at: datetime | None = None
    referral_count: int = 0


class PromoCodeSummary(BaseModel):
    total_referrals: int = 0
    used_code_count: int = 0
    rewarded_registrations: int = 0


class PromoCodeListResponse(BaseModel):
    summary: PromoCodeSummary
    items: list[PromoCodeItem]


class PromoReferralItem(BaseModel):
    user_id: str
    username: str
    email_masked: str = "-"
    email: str | None = None
    promo_code: str = ""
    platform_name: str = ""
    reward_credits: int = 0
    registered_at: datetime | None = None


class PromoReferralListResponse(BaseModel):
    total: int
    items: list[PromoReferralItem]


class PromoReferralActivityItem(BaseModel):
    user_id: str
    username: str
    email_masked: str = "-"
    activity_type: str
    credits: int = 0
    amount_fen: int | None = None
    amount_yuan: float | None = None
    redeem_key: str = ""
    order_no: str = ""
    occurred_at: datetime | None = None


class PromoReferralActivityListResponse(BaseModel):
    total: int
    items: list[PromoReferralActivityItem]


class PromoCodeValidationResponse(BaseModel):
    valid: bool
    code: str = ""
    platform_name: str = ""
