
# Устанавливаем зависимости

!pip install -q \
    transformers>=4.40 \
    accelerate>=0.30 \
    peft>=0.12 \
    datasets \
    trl \
    safetensors \
    sentencepiece

# Импортируем библиотеки

import transformers, accelerate, peft, torch
print("Transformers:", transformers.__version__)
print("Accelerate:", accelerate.__version__)
print("PEFT:", peft.__version__)
print("Torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

# Устанавливаем bitsandbytes

!pip uninstall -y bitsandbytes
!pip install -q bitsandbytes==0.45.1 --no-cache-dir

# Загружаем модель и новые веса. Важно, чтобы в папке my-lora-adapter были файлы adapter_config.json и файл формата .safetensors - веса модели

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

model = AutoModelForCausalLM.from_pretrained(
    "unsloth/Qwen2.5-7B-Instruct",
    load_in_4bit=True,
    device_map="auto",
    trust_remote_code=True,
    use_cache=False,
)

tokenizer = AutoTokenizer.from_pretrained("unsloth/Qwen2.5-7B-Instruct", trust_remote_code=True)

model = PeftModel.from_pretrained(model, "./my-lora-adapter")



# Создаем функцию для истории чата

def chat_with_history(history, new_user_message, max_new_tokens=512):
    """
    Добавляет новый вопрос пользователя в историю,
    генерирует ответ модели и добавляет его в историю.
    Возвращает обновлённую историю и ответ.
    """
    # Добавляем новый вопрос
    history.append({"role": "user", "content": new_user_message})

    # Форматируем весь диалог
    text = tokenizer.apply_chat_template(
        history,
        tokenize=False,
        add_generation_prompt=True  # добавляет <|im_start|>assistant
    )

    # Токенизируем
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=4096  # убедитесь, что это >= max_seq_length при обучении
    ).to("cuda")

    # Генерация
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        pad_token_id=tokenizer.eos_token_id
    )

    # Извлекаем только сгенерированный ответ
    response_tokens = outputs[0][inputs.input_ids.shape[1]:]
    response = tokenizer.decode(response_tokens, skip_special_tokens=True).strip()

    # Добавляем ответ в историю
    history.append({"role": "assistant", "content": response})

    return history, response

# Ограничваем по ширине контекстное окно вывода

import textwrap

def wrap_paragraphs(text, width=80):
    paragraphs = text.split("\n\n")
    wrapped = [textwrap.fill(p, width=width) for p in paragraphs]
    return "\n\n".join(wrapped)

# Начинаем с пустой истории
history = []

print("Диалог с дообученной моделью (введите 'exit' для выхода)\n")

while True:
    user_input = input("Вы: ")
    if user_input.lower() == "exit":
        break

    history, response = chat_with_history(history, user_input)

    wrapped_response = wrap_paragraphs(response, width=80)


    print(f"\nМодель: {wrapped_response}\n")
    print("-" * 50)

