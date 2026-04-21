"""
配置管理模型 - Pydantic V2 兼容版本
"""
from pydantic import BaseModel, Field, field_validator, model_validator, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class LLMConfig(BaseModel):
    """LLM配置"""
    api_key: str = Field(
        ...,
        description="API密钥",
        min_length=10
    )
    model: str = Field(
        default="gpt-3.5-turbo",
        description="模型名称"
    )
    base_url: Optional[str] = Field(
        None,
        description="API端点URL"
    )
    temperature: float = Field(
        default=0.7,
        ge=0,
        le=2,
        description="温度参数，控制输出随机性"
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=32000,
        description="最大token数"
    )
    timeout: int = Field(
        default=60,
        ge=1,
        le=300,
        description="请求超时时间(秒)"
    )
    retry_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="重试次数"
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="重试延迟(秒)"
    )

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        """验证API密钥格式"""
        if not v or v.strip() == "":
            raise ValueError("API密钥不能为空")

        # 检查是否是占位符
        if v in ["your_api_key_here", "sk-xxx", "xxx"]:
            raise ValueError("请设置有效的API密钥")

        return v.strip()

    @field_validator('model')
    @classmethod
    def validate_model(cls, v):
        """验证模型名称"""
        valid_models = [
            # OpenAI
            "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo",
            # 阿里云百炼
            "qwen-plus", "qwen-turbo", "qwen-max",
            # DeepSeek
            "deepseek-chat", "deepseek-coder",
            # 其他
            "claude-3-sonnet", "claude-3-haiku"
        ]

        # 允许自定义模型名称，只是给出警告
        if v not in valid_models:
            print(f"警告: 使用了未知的模型名称 '{v}'，请确保该模型可用")

        return v


class TestConfig(BaseModel):
    """测试配置"""
    base_url: str = Field(
        default="https://example.com",
        description="测试基础URL"
    )
    timeout: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="测试超时时间(毫秒)"
    )
    headed: bool = Field(
        default=False,
        description="是否使用有头模式运行浏览器"
    )
    browser: str = Field(
        default="chromium",
        pattern=r"^(chromium|firefox|webkit)$",
        description="浏览器类型"
    )
    viewport_width: int = Field(
        default=1280,
        ge=800,
        le=3840,
        description="视口宽度"
    )
    viewport_height: int = Field(
        default=720,
        ge=600,
        le=2160,
        description="视口高度"
    )
    slow_mo: int = Field(
        default=0,
        ge=0,
        le=5000,
        description="慢动作延迟(毫秒)，用于调试"
    )
    screenshot_on_failure: bool = Field(
        default=True,
        description="失败时是否截图"
    )
    video_recording: bool = Field(
        default=False,
        description="是否录制视频"
    )

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v):
        """验证基础URL格式"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("base_url 必须以 http:// 或 https:// 开头")
        return v.rstrip('/')


class AllureConfig(BaseModel):
    """Allure配置"""
    results_dir: str = Field(
        default="allure-results",
        description="测试结果目录"
    )
    report_dir: str = Field(
        default="allure-report",
        description="测试报告目录"
    )
    server_port: int = Field(
        default=8080,
        ge=1024,
        le=65535,
        description="报告服务器端口"
    )
    clean_results: bool = Field(
        default=True,
        description="生成报告前是否清理旧结果"
    )
    open_browser: bool = Field(
        default=True,
        description="生成报告后是否自动打开浏览器"
    )


class LogConfig(BaseModel):
    """日志配置"""
    level: str = Field(
        default="INFO",
        pattern=r"^(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL)$",
        description="日志级别"
    )
    file: Optional[str] = Field(
        None,
        description="日志文件路径，None表示只输出到控制台"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    max_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="日志文件最大大小(MB)"
    )
    backup_count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="日志文件备份数量"
    )


class WorkflowConfig(BaseModel):
    """工作流配置"""
    max_iterations: int = Field(
        default=2,
        ge=1,
        le=10,
        description="最大迭代次数"
    )
    review_threshold: float = Field(
        default=60.0,
        ge=0.0,
        le=100.0,
        description="评审通过阈值(分数)"
    )
    parallel_execution: bool = Field(
        default=False,
        description="是否并行执行测试"
    )
    auto_retry: bool = Field(
        default=True,
        description="失败时是否自动重试"
    )


class ProjectSettings(BaseSettings):
    """项目配置 - 支持环境变量"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 忽略未定义的环境变量
    )

    # LLM配置 - 使用 validation_alias 映射环境变量
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices('llm_api_key', 'LLM_KEY'),
        description="LLM API密钥"
    )
    llm_model: str = Field(
        default="gpt-3.5-turbo",
        validation_alias=AliasChoices('llm_model', 'LLM_MODEL'),
        description="LLM模型"
    )
    llm_base_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('llm_base_url', 'LLM_BASE_URL'),
        description="LLM API端点"
    )
    llm_temperature: float = Field(default=0.7, description="LLM温度")
    llm_max_tokens: int = Field(default=8192, description="LLM最大tokens")
    llm_timeout: int = Field(default=60, description="LLM超时时间")
    llm_retry_attempts: int = Field(default=3, description="LLM重试次数")
    llm_retry_delay: float = Field(default=1.0, description="LLM重试延迟(秒)")

    # Midscene AI 配置
    openai_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('openai_api_key', 'OPENAI_API_KEY'),
        description="Midscene/OpenAI API密钥"
    )
    openai_base_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('openai_base_url', 'OPENAI_BASE_URL'),
        description="Midscene/OpenAI API端点"
    )
    midscene_model_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('midscene_model_name', 'MIDSCENE_MODEL_NAME'),
        description="Midscene模型名称"
    )
    midscene_use_qwen_vl: bool = Field(
        default=False,
        description="是否使用Qwen VL模型"
    )

    # 测试配置
    test_base_url: str = Field(
        default="https://example.com",
        validation_alias=AliasChoices('test_base_url', 'TEST_BASE_URL')
    )
    test_timeout: int = Field(
        default=30000,
        validation_alias=AliasChoices('test_timeout', 'TEST_TIMEOUT')
    )
    test_headed: bool = Field(default=False)
    test_browser: str = Field(default="chromium")

    # Allure配置
    allure_results_dir: str = Field(default="allure-results")
    allure_report_dir: str = Field(default="allure-report")
    allure_server_port: int = Field(default=8080)

    # 日志配置
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices('log_level', 'LOG_LEVEL')
    )
    log_file: Optional[str] = Field(default=None)

    # 工作流配置
    max_iterations: int = Field(default=2)
    review_threshold: float = Field(default=60.0)

    def get_llm_config(self) -> LLMConfig:
        """获取LLM配置对象"""
        return LLMConfig(
            api_key=self.llm_api_key,
            model=self.llm_model,
            base_url=self.llm_base_url,
            temperature=self.llm_temperature,
            max_tokens=self.llm_max_tokens,
            timeout=self.llm_timeout
        )

    def get_test_config(self) -> TestConfig:
        """获取测试配置对象"""
        return TestConfig(
            base_url=self.test_base_url,
            timeout=self.test_timeout,
            headed=self.test_headed,
            browser=self.test_browser
        )

    def get_allure_config(self) -> AllureConfig:
        """获取Allure配置对象"""
        return AllureConfig(
            results_dir=self.allure_results_dir,
            report_dir=self.allure_report_dir,
            server_port=self.allure_server_port
        )

    def get_log_config(self) -> LogConfig:
        """获取日志配置对象"""
        return LogConfig(
            level=self.log_level,
            file=self.log_file
        )

    def get_workflow_config(self) -> WorkflowConfig:
        """获取工作流配置对象"""
        return WorkflowConfig(
            max_iterations=self.max_iterations,
            review_threshold=self.review_threshold
        )


# 全局配置实例
_settings_instance = None

def get_settings() -> ProjectSettings:
    """获取项目配置实例（单例模式）"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = ProjectSettings()
    return _settings_instance