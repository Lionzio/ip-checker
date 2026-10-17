# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L1-Q6, sem nenhum código de aluno. Revise antes do merge.
def main():
    login = input()
    senha = input()

    print("Byte irá julgar a sua senha.")

    # Requisitos obrigatórios
    # - Possuir ao menos 8 caracteres.
    # - Não conter apenas letras ou apenas números.
    # - Não possuir espaço.
    
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

    # Comprimento: a cada caractere que ultrapassar 11 caracteres, a senha ganha 1 ponto
    if len(senha) > 11:
        pontos += (len(senha) - 11)

    # Mistura de maiúsculas e minúsculas: se a senha tiver ao menos uma letra maiúscula e uma minúscula, ela ganha 5 pontos
    tem_maiuscula = any(c.isupper() for c in senha)
    tem_minuscula = any(c.islower() for c in senha)
    if tem_maiuscula and tem_minuscula:
        pontos += 5

    # Caracteres especiais: para cada símbolo diferente entre @ _ & % # que aparecer na senha (pelo menos uma vez), ela ganha 1 ponto
    especiais = "@_&%#"
    for esp in especiais:
        if esp in senha:
            pontos += 1

    # Login escondido na senha: se a senha contiver o login do usuário (independente de maiúscula ou minúscula), perde 10 pontos
    if login.lower() in senha.lower():
        pontos -= 10

    # Se tiver mais de 14 caracteres
    if len(senha) > 14:
        print("Que senha grande! Não seria difícil esquecer dela.")

    # Se o login for encontrado dentro da senha
    if login.lower() in senha.lower():
        print("Olha o que eu encontrei aqui, não deixarei isso passar tão fácil.")

    # Terminando a análise:
    if pontos < 1:
        print("Infelizmente terá que mudar sua senha, é para o seu bem.")
        faltam = 1 - pontos
        print(f"Melhore sua senha em {faltam} ponto(s) e ela será suficiente.")
    elif 1 <= pontos <= 10:
        print("Pode manter a sua senha, ela parece adequada.")
    else:
        print("Parabéns! Nem o maior hacker do mundo encontraria uma senha assim.")

if __name__ == '__main__':
    main()
