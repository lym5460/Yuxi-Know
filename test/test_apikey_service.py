"""API Key Service 单元测试

测试 API Key 的生成、哈希和格式验证。
包含属性测试验证核心正确性属性。

Property 1: API Key 格式一致性
Property 2: 密钥存储安全性
Validates: Requirements 1.2, 1.4
"""

import hashlib
import os
import re
import sys

# Add project root to path
sys.path.insert(0, os.getcwd())

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.services.apikey_service import (
    API_KEY_PREFIX,
    API_KEY_RANDOM_LENGTH,
    KEY_PREFIX_DISPLAY_LENGTH,
    generate_api_key,
    get_key_prefix,
    hash_api_key,
)


class TestAPIKeyGeneration:
    """API Key 生成函数测试"""

    def test_generate_api_key_format(self):
        """测试生成的 API Key 格式正确"""
        key = generate_api_key()

        # 验证前缀
        assert key.startswith(API_KEY_PREFIX), f"API Key 应以 '{API_KEY_PREFIX}' 开头"

        # 验证总长度
        expected_length = len(API_KEY_PREFIX) + API_KEY_RANDOM_LENGTH
        assert len(key) == expected_length, f"API Key 长度应为 {expected_length}"

    def test_generate_api_key_uniqueness(self):
        """测试生成的 API Key 唯一性"""
        keys = [generate_api_key() for _ in range(100)]
        unique_keys = set(keys)

        assert len(unique_keys) == len(keys), "生成的 API Key 应该是唯一的"

    def test_generate_api_key_characters(self):
        """测试生成的 API Key 只包含有效字符"""
        key = generate_api_key()
        random_part = key[len(API_KEY_PREFIX) :]

        # URL-safe base64 字符: a-z, A-Z, 0-9, -, _
        valid_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
        assert valid_pattern.match(random_part), "API Key 随机部分应只包含 URL-safe 字符"


class TestAPIKeyHash:
    """API Key 哈希函数测试"""

    def test_hash_api_key_format(self):
        """测试哈希值格式正确（64位十六进制）"""
        key = generate_api_key()
        key_hash = hash_api_key(key)

        assert len(key_hash) == 64, "SHA256 哈希应为 64 位十六进制字符"
        assert all(c in "0123456789abcdef" for c in key_hash), "哈希应只包含十六进制字符"

    def test_hash_api_key_consistency(self):
        """测试相同密钥产生相同哈希"""
        key = generate_api_key()
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)

        assert hash1 == hash2, "相同密钥应产生相同哈希"

    def test_hash_api_key_different_keys(self):
        """测试不同密钥产生不同哈希"""
        key1 = generate_api_key()
        key2 = generate_api_key()

        hash1 = hash_api_key(key1)
        hash2 = hash_api_key(key2)

        assert hash1 != hash2, "不同密钥应产生不同哈希"

    def test_hash_api_key_sha256_correctness(self):
        """测试哈希计算正确性"""
        test_key = "yk_test1234567890abcdefghijklmnop"
        expected_hash = hashlib.sha256(test_key.encode("utf-8")).hexdigest()

        actual_hash = hash_api_key(test_key)

        assert actual_hash == expected_hash, "哈希计算应与标准 SHA256 一致"


class TestAPIKeyPrefix:
    """API Key 前缀提取测试"""

    def test_get_key_prefix(self):
        """测试前缀提取正确"""
        key = generate_api_key()
        prefix = get_key_prefix(key)

        assert len(prefix) == KEY_PREFIX_DISPLAY_LENGTH, f"前缀长度应为 {KEY_PREFIX_DISPLAY_LENGTH}"
        assert key.startswith(prefix), "前缀应是密钥的开头部分"

    def test_get_key_prefix_contains_yk(self):
        """测试前缀包含 yk_ 标识"""
        key = generate_api_key()
        prefix = get_key_prefix(key)

        assert prefix.startswith(API_KEY_PREFIX), f"前缀应以 '{API_KEY_PREFIX}' 开头"


# =============================================================================
# === 属性测试 (Property-Based Tests) ===
# =============================================================================


class TestAPIKeyProperties:
    """API Key 属性测试

    使用 hypothesis 进行属性测试，验证核心正确性属性。
    """

    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=100))
    def test_property_1_api_key_format_consistency(self, _iteration: int):
        """Property 1: API Key 格式一致性

        For any 创建的 API Key，其格式必须为 `yk_` 前缀加 32 位随机字符，
        且每个密钥都是唯一的。

        **Validates: Requirements 1.2**
        """
        key = generate_api_key()

        # 验证前缀
        assert key.startswith(API_KEY_PREFIX), f"API Key 必须以 '{API_KEY_PREFIX}' 开头"

        # 验证随机部分长度
        random_part = key[len(API_KEY_PREFIX) :]
        assert len(random_part) == API_KEY_RANDOM_LENGTH, f"随机部分长度必须为 {API_KEY_RANDOM_LENGTH}"

        # 验证字符集（URL-safe base64）
        valid_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
        assert valid_pattern.match(random_part), "随机部分必须只包含 URL-safe 字符"

    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=100))
    def test_property_2_key_storage_security(self, _iteration: int):
        """Property 2: 密钥存储安全性

        For any 存储在数据库中的 API Key 记录，key_hash 字段必须是原始密钥的
        SHA256 哈希值，且数据库中不存储明文密钥。

        **Validates: Requirements 1.4**
        """
        # 生成密钥
        raw_key = generate_api_key()

        # 计算哈希
        key_hash = hash_api_key(raw_key)

        # 验证哈希是 SHA256 格式（64位十六进制）
        assert len(key_hash) == 64, "哈希必须是 64 位十六进制字符"
        assert all(c in "0123456789abcdef" for c in key_hash), "哈希必须只包含十六进制字符"

        # 验证哈希计算正确性
        expected_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        assert key_hash == expected_hash, "哈希必须与标准 SHA256 计算结果一致"

        # 验证无法从哈希反推明文（哈希不包含原始密钥）
        assert raw_key not in key_hash, "哈希不应包含原始密钥"
        assert key_hash != raw_key, "哈希不应等于原始密钥"

    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=100))
    def test_property_uniqueness(self, _iteration: int):
        """验证每次生成的 API Key 都是唯一的"""
        keys = [generate_api_key() for _ in range(10)]
        unique_keys = set(keys)

        assert len(unique_keys) == len(keys), "每次生成的 API Key 必须是唯一的"

    @settings(max_examples=100)
    @given(st.text(min_size=1, max_size=100))
    def test_property_hash_deterministic(self, input_text: str):
        """验证哈希函数是确定性的"""
        hash1 = hash_api_key(input_text)
        hash2 = hash_api_key(input_text)

        assert hash1 == hash2, "相同输入必须产生相同哈希"

    @settings(max_examples=100)
    @given(st.text(min_size=1, max_size=50), st.text(min_size=1, max_size=50))
    def test_property_hash_collision_resistance(self, text1: str, text2: str):
        """验证不同输入产生不同哈希（碰撞抵抗）"""
        if text1 == text2:
            return  # 跳过相同输入

        hash1 = hash_api_key(text1)
        hash2 = hash_api_key(text2)

        assert hash1 != hash2, "不同输入应产生不同哈希"
