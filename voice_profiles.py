#!/usr/bin/env python3
"""
Voice Profiles Configuration Manager
管理声音克隆的参考音频和参考文本配置

目录结构:
  ref/
    01/
      voice.m4a (或 voice.wav, voice.mp3)
      ref.txt
      meta.json (可选，包含 name 和 description)
    02/
      voice.wav
      ref.txt
      meta.json
"""

import os
import json
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class VoiceProfile:
    """声音配置文件"""
    id: str  # 文件夹名 (如 "01", "02")
    name: str  # 显示名称
    description: str
    ref_audio: str  # 音频文件完整路径
    ref_text: str  # 参考文本


class VoiceProfileManager:
    """声音配置管理器"""
    
    AUDIO_EXTENSIONS = [".m4a", ".wav", ".mp3", ".ogg", ".flac"]
    
    def __init__(self, ref_dir: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            ref_dir: 配置文件目录路径，默认为项目根目录下的 ref 文件夹
        """
        if ref_dir is None:
            self.ref_dir = os.path.join(os.path.dirname(__file__), "ref")
        else:
            self.ref_dir = ref_dir
        
        os.makedirs(self.ref_dir, exist_ok=True)
    
    def list_profiles(self) -> List[str]:
        """列出所有可用的声音配置 ID"""
        profiles = []
        for item in os.listdir(self.ref_dir):
            item_path = os.path.join(self.ref_dir, item)
            if os.path.isdir(item_path):
                # 检查是否有 ref.txt 和音频文件
                ref_txt = os.path.join(item_path, "ref.txt")
                if os.path.exists(ref_txt):
                    profiles.append(item)
        return sorted(profiles)
    
    def _find_audio_file(self, profile_dir: str) -> Optional[str]:
        """在配置目录中查找音频文件"""
        for ext in self.AUDIO_EXTENSIONS:
            audio_file = os.path.join(profile_dir, f"voice{ext}")
            if os.path.exists(audio_file):
                return audio_file
        return None
    
    def load_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        """
        加载指定的声音配置
        
        Args:
            profile_id: 配置 ID（文件夹名，如 "01", "02"）
        
        Returns:
            VoiceProfile 对象，如果不存在则返回 None
        """
        profile_dir = os.path.join(self.ref_dir, profile_id)
        
        if not os.path.isdir(profile_dir):
            return None
        
        # 读取 ref.txt
        ref_txt_path = os.path.join(profile_dir, "ref.txt")
        if not os.path.exists(ref_txt_path):
            return None
        
        try:
            with open(ref_txt_path, "r", encoding="utf-8") as f:
                ref_text = f.read().strip()
        except Exception as e:
            print(f"Error reading ref.txt: {e}")
            return None
        
        # 查找音频文件
        audio_file = self._find_audio_file(profile_dir)
        if not audio_file:
            print(f"Error: No audio file found in {profile_dir}")
            return None
        
        # 读取 meta.json（可选）
        name = profile_id
        description = ""
        meta_path = os.path.join(profile_dir, "meta.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    name = meta.get("name", profile_id)
                    description = meta.get("description", "")
            except Exception:
                pass
        
        return VoiceProfile(
            id=profile_id,
            name=name,
            description=description,
            ref_audio=audio_file,
            ref_text=ref_text
        )
    
    def create_profile(self, profile_id: str, name: str, description: str,
                       ref_text: str, audio_source: str) -> Optional[VoiceProfile]:
        """
        创建新的声音配置
        
        Args:
            profile_id: 配置 ID（文件夹名）
            name: 显示名称
            description: 描述
            ref_text: 参考文本
            audio_source: 源音频文件路径
        
        Returns:
            新创建的 VoiceProfile 对象
        """
        import shutil
        
        profile_dir = os.path.join(self.ref_dir, profile_id)
        
        try:
            os.makedirs(profile_dir, exist_ok=True)
            
            # 复制音频文件
            _, ext = os.path.splitext(audio_source)
            if ext.lower() not in self.AUDIO_EXTENSIONS:
                ext = ".m4a"
            
            audio_dest = os.path.join(profile_dir, f"voice{ext}")
            shutil.copy2(audio_source, audio_dest)
            
            # 写入 ref.txt
            with open(os.path.join(profile_dir, "ref.txt"), "w", encoding="utf-8") as f:
                f.write(ref_text)
            
            # 写入 meta.json
            with open(os.path.join(profile_dir, "meta.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "name": name,
                    "description": description
                }, f, ensure_ascii=False, indent=2)
            
            return VoiceProfile(
                id=profile_id,
                name=name,
                description=description,
                ref_audio=audio_dest,
                ref_text=ref_text
            )
        except Exception as e:
            print(f"Error creating profile: {e}")
            return None


def main():
    """测试配置管理器"""
    manager = VoiceProfileManager()
    
    print("可用的声音配置：")
    print("-" * 60)
    for profile_id in manager.list_profiles():
        profile = manager.load_profile(profile_id)
        if profile:
            print(f"\n[{profile.id}] {profile.name}")
            print(f"    描述: {profile.description}")
            print(f"    音频: {os.path.basename(profile.ref_audio)}")
            print(f"    文本: {profile.ref_text[:40]}...")


if __name__ == "__main__":
    main()