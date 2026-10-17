# Solução gerada por IA (S42-04, ADR-08): qwen, modelo qwen/qwen3.8-27b, 17/10/2026.
# Só a partir do enunciado da L1-Q4, sem nenhum código de aluno. Revise antes do merge.
chuva = input()
temp = int(input())
energia = int(input())

if chuva == "S":
    if energia > 3:
        print("Brincar de bolinha no laboratório")
    else:
        print("Soneca na caminha do CIn")
else:
    if temp > 30:
        if energia >= 4:
            print("Nadar no lago da UFPE")
        else:
            print("Descansar na sombra da árvore")
    elif 14 < temp < 31:
        if energia > 2:
            print("Longo passeio no parque")
        else:
            print("Passeio curto no quarteirão")
    elif temp < 15:
        print("Passeio com roupinha de frio")
