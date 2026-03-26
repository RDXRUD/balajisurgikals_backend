from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGODB_URI: str
    MONGODB_DB: str = "balaji_surgikals"

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    ADMIN_EMAIL: str = "admin@balajisurgikals.com"
    ADMIN_PASSWORD: str = "admin123"

    # Oracle Cloud Object Storage (S3-compatible)
    OCI_NAMESPACE: str = ""
    OCI_REGION: str = "ap-mumbai-1"
    OCI_BUCKET: str = ""
    OCI_ACCESS_KEY: str = ""
    OCI_SECRET_KEY: str = ""

    @property
    def OCI_ENDPOINT(self) -> str:
        return f"https://{self.OCI_NAMESPACE}.compat.objectstorage.{self.OCI_REGION}.oraclecloud.com"

    @property
    def OCI_PUBLIC_URL_BASE(self) -> str:
        return f"https://objectstorage.{self.OCI_REGION}.oraclecloud.com/n/{self.OCI_NAMESPACE}/b/{self.OCI_BUCKET}/o"

    class Config:
        env_file = ".env"


settings = Settings()
