# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-120b, 17/10/2026.
# Só a partir do enunciado da L1-Q4, sem nenhum código de aluno. Revise antes do merge.
chove = input().strip()
temp = int(input().strip())
energia = int(input().strip())

if chove == 'S':
    if energia > 3:
        print("Brincar de bolinha no laboratório")
    else:
        print("Soneca na caminha do CIn")
else:  # não está chovendo
    if temp > 30:
        if energia >= 4:
            print("Nadar no lago da UFPE")
        else:
            print("Descansar na sombra da árvore")
    elif 15 <= temp <= 30:
        if energia > 2:
            print("Longo passeio no parque")
        else:
            print("Passeio curto no quarteirão")
    else:  # temp < 15
        print("Passeio com roupinha de frio")
