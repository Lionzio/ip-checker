# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-120b, 17/10/2026.
# Só a partir do enunciado da L1-Q6, sem nenhum código de aluno. Revise antes do merge.
login = input().strip()
senha = input().strip()

print("Byte irá julgar a sua senha.")

# requisitos obrigatórios
if len(senha) < 8 or senha.isalpha() or senha.isdigit() or ' ' in senha:
    print("Essa senha nem chega perto do que eu aceito. Tente de novo.")
else:
    print("Vamos fazer a contagem dos pontos.")

    pontos = 0

    # comprimento acima de 11
    if len(senha) > 11:
        pontos += len(senha) - 11

    # mistura de maiúsculas e minúsculas
    tem_maiuscula = any(c.isupper() for c in senha)
    tem_minuscula = any(c.islower() for c in senha)
    if tem_maiuscula and tem_minuscula:
        pontos += 5

    # caracteres especiais distintos
    especiais = {'@', '_', '&', '%', '#'}
    presentes = set(senha) & especiais
    pontos += len(presentes)

    # login escondido
    if login.lower() in senha.lower():
        pontos -= 10
        login_encontrado = True
    else:
        login_encontrado = False

    # mensagens intermediárias
    if len(senha) > 14:
        print("Que senha grande! Não seria difícil esquecer dela.")
    if login_encontrado:
        print("Olha o que eu encontrei aqui, não deixarei isso passar tão fácil.")

    # avaliação final
    if pontos < 1:
        faltam = 1 - pontos
        print("Infelizmente terá que mudar sua senha, é para o seu bem.")
        print(f"Melhore sua senha em {faltam} ponto(s) e ela será suficiente.")
    elif pontos < 11:
        print("Pode manter a sua senha, ela parece adequada.")
    else:
        print("Parabéns! Nem o maior hacker do mundo encontraria uma senha assim.")
