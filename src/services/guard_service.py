import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class GuardService:
    def __init__(self,model_id='meta-llama/Llama-Prompt-Guard-2-22M'):
        self.model=AutoModelForSequenceClassification.from_pretrained(model_id)
        self.tokenizer=AutoTokenizer.from_pretrained(model_id)

    def guard(self,input):
        """This function guides against unsafe user input"""
        inputs = self.tokenizer(input, return_tensors="pt")

        with torch.no_grad():
            logits = self.model(**inputs).logits
        predicted_class_id = logits.argmax().item()
        is_safe=self.model.config.id2label[predicted_class_id]
        if is_safe=='LABEL_0':
            return True

