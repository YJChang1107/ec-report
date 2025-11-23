import google.generativeai as genai
import os

print(f"GenAI Version: {genai.__version__}")
print("Attributes in genai.types:")
try:
    for item in dir(genai.types):
        if "Search" in item:
            print(f" - {item}")
except Exception as e:
    print(f"Error inspecting types: {e}")

print("\nAttributes in genai.protos:")
try:
    for item in dir(genai.protos):
        if "Search" in item:
            print(f" - {item}")
except Exception as e:
    print(f"Error inspecting protos: {e}")
