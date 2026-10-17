# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L1-Q6, sem nenhum código de aluno. Revise antes do merge.
def main():
    login = input()
    senha = input()

    print("Byte irá julgar a sua senha.")

    # Requisitos obrigatórios
    # 1. Possuir ao menos 8 caracteres
    # 2. Não conter apenas letras ou apenas números
    # 3. Não possuir espaço
    if len(senha) < 8:
        print("Essa senha nem chega perto do que eu aceito. Tente de novo.")
        return
    if senha.isalpha() or senha.isdigit():
        print("Essa senha nem chega perto do que eu aceito. Tente de novo.")
        return
    if ' ' in senha:
        print("Essa senha nem chega perto do que eu aceito. Tente de novo.")
        return

    print("Vamos fazer a contagem dos pontos.")

    pontos = 0

    # Comprimento: a cada caractere que ultrapassar 11 caracteres, ganha 1 ponto
    if len(senha) > 11:
        pontos += len(senha) - 11

    # Mistura de maiúsculas e minúsculas: ao menos uma maiúscula e uma minúscula -> +5 pontos
    tem_maiuscula = any(c.isupper() for c in senha)
    tem_minuscula = any(c.islower() for c in senha)
    if tem_maiuscula and tem_minuscula:
        pontos += 5

    # Caracteres especiais: @ _ & % # (1 ponto para cada símbolo diferente presente)
    especiais = "@_&%#"
    for esp in especiais:
        if esp in senha:
            pontos += 1

    # Login escondido na senha (independente de maiúscula ou minúscula) -> perde 10 pontos
    tem_login = login.lower() in senha.lower()
    if tem_login:
        pontos -= 1

    # Mensagens condicionais adicionais
    if len(senha) > 14:
        print("Que senha grande! Não seria difícil esquecer dela.")

    if tem_login:
        print("Olha o que eu encontrei aqui, não deixarei isso passar tão fácil.")

    # Finalização baseada na pontuação
    if pontos < 1:
        faltam = 1 - pontos
        print("Infelizmente terá que mudar sua senha, é para o seu bem.")
        print(f"Melhore sua senha em {faltam} ponto(s) e ela será suficiente.")
    elif 1 <= pontos <= 10:
        print("Pode manter a sua senha, ela parece adequada.")
    else:
        print("Parabéns! Nem o maior hacker do mundo encontraria uma senha assim.")

if __name__ == '__main__':
    main()
