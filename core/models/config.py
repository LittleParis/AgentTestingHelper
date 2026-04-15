"""
配置管理模型
"""
from pydantic import BaseSettings, BaseModel, Field, validator
from typing import Optional
import os


class LLMConfig(BaseModel):
    """LLM配置"""
    api_key: str = Field(
        ..., 
        description="API密钥",
        min_length=10
    )
    model: str = Field(
        default="gpt-3.5-turbo", 
        description="模型名称",
        example="gpt-4"
    )
    base_url: Optional[str] = Field(
        None, 
        description="API端点URL",
        example="https://api.openai.com/v1"
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
    
    @validator('api_key')
    def validate_api_key(cls, v):
        """验证API密钥格式"""
        if not v or v.strip() == "":
            raise ValueError("API密钥不能为空")
        
        # 检查是否是占位符
        if v in ["your_api_key_here", "sk-xxx", "xxx"]:
            raise ValueError("请设置有效的API密钥")
        
        return v.strip()
    
    @validator('model')
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
    
    class Config:
        schema_extra = {
            "example": {
                "api_key": "sk-1234567890abcdef",
                "model": "gpt-4",
                "base_url": "https://api.openai.com/v1",
                "temperature": 0.7,
                "max_tokens": 4096,
                "timeout": 60,
                "retry_attempts": 3,
                "retry_delay": 1.0
            }
        }


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
    
    @validator('base_url')
    def validate_base_url(cls, v):
        """验证基础URL格式"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("base_url 必须以 http:// 或 https:// 开头")
        return v.rstrip('/')
    
    class Config:
        schema_extra = {
            "example": {
                "base_url": "https://example.com",
                "timeout": 30000,
                "headed": False,
                "browser": "chromium",
                "viewport_width": 1280,
                "viewport_height": 720,
                "slow_mo": 0,
                "screenshot_on_failure": True,
                "video_recording": False
            }
        }


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
    
    class Config:
        schema_extra = {
            "example": {
                "results_dir": "allure-results",
                "report_dir": "allure-report", 
                "server_port": 8080,
                "clean_results": True,
                "open_browser": True
            }
        }


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
    
    class Config:
        schema_extra = {
            "example": {
                "level": "INFO",
                "file": "logs/app.log",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "max_size": 10,
                "backup_count": 5
            }
        }


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
    
    class Config:
        schema_extra = {
            "example": {
                "max_iterations": 2,
                "review_threshold": 60.0,
                "parallel_execution": False,
                "auto_retry": True
            }
        }


class ProjectSettings(BaseSettings):
    """项目配置 - 支持环境变量"""
    
    # LLM配置
    llm_api_key: str = Field(..., env="LLM_KEY", description="LLM API密钥")
    llm_model: str = Field(default="gpt-3.5-turbo", env="LLM_MODEL", description="LLM模型")
    llm_base_url: Optional[str] = Field(None, env="LLM_BASE_URL", description="LLM API端点")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE", description="LLM温度")
    llm_max_tokens: int = Field(default=4096, env="LLM_MAX_TOKENS", description="LLM最大tokens")
    llm_timeout: int = Field(default=60, env="LLM_TIMEOUT", description="LLM超时时间")
    
    # 测试配置
    test_base_url: str = Field(default="https://example.com", env="TEST_BASE_URL")
    test_timeout: int = Field(default=30000, env="TEST_TIMEOUT")
    test_headed: bool = Field(default=False, env="TEST_HEADED")
    test_browser: str = Field(default="chromium", env="TEST_BROWSER")
    
    # Allure配置
    allure_results_dir: str = Field(default="allure-results", env="ALLURE_RESULTS_DIR")
    allure_report_dir: str = Field(default="allure-report", env="ALLURE_REPORT_DIR")
    allure_server_port: int = Field(default=8080, env="ALLURE_SERVER_PORT")
    
    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(None, env="LOG_FILE")
    
    # 工作流配置
    max_iterations: int = Field(default=2, env="MAX_ITERATIONS")
    review_threshold: float = Field(default=60.0, env="REVIEW_THRESHOLD")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
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
def get_settings() -> ProjectSettings:
    """获取项目配置实例"""
    return ProjectSettings()