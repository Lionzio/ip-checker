# Solução gerada por IA (S42-04, ADR-08): qwen, modelo qwen/qwen3.8-27b, 17/10/2026.
# Só a partir do enunciado da L1-Q2, sem nenhum código de aluno. Revise antes do merge.
energia_byte = int(input())
quantidade_petiscos = int(input())
quantidade_agua = int(input())
bateria_coleira = int(input())
gps = input()
bolinha = input()
chuva = input()
temperatura = int(input())
intensidade_sinal = int(input())

preparo = 0

print("Byte recebeu um novo chamado! Preparando-se para a aventura...")

if energia_byte >= 70:
    print("Byte está cheio de energia!")
    preparo += 2
elif energia_byte < 30:
    print("Byte está muito cansado... A missão ficou mais difícil.")
    preparo -= 2

if quantidade_petiscos >= 2 and quantidade_agua >= 1:
    print("Suprimentos preparados!")
    preparo += 2

if bateria_coleira >= 50 and gps == "sim":
    print("Coleira tecnológica preparada!")
    preparo += 2

if bateria_coleira <= 20:
    print("A bateria da coleira está crítica! Isso pode atrapalhar a missão.")
    preparo -= 1

if bolinha == "sim" or quantidade_petiscos >= 4:
    print("Byte está ainda mais animado para a aventura!")
    preparo += 1

if chuva == "sim" or temperatura > 32:
    print("O clima não está ajudando... Isso vai dificultar a missão.")
    preparo -= 2

if intensidade_sinal >= 70:
    print("O sinal está forte! Há algo estranho por perto...")
    preparo += 1

print()
print(f"Nível de preparo: {preparo}")

if preparo >= 5:
    print("Byte está pronto! A nova aventura começa agora!")
else:
    print("Byte ainda não está pronto. Melhor se preparar um pouco mais!")
