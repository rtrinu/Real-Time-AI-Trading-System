from transformers import pipeline

pipe = pipeline("text-classification", model="ProsusAI/finbert")
