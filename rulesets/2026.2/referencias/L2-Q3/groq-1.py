# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-120b, 17/10/2026.
# Só a partir do enunciado da L2-Q3, sem nenhum código de aluno. Revise antes do merge.
def main():
    try:
        paciencia = int(input().strip())
    except:
        return

    print("Shrek achava que morar em um pântano afastado seria suficiente para manter as pessoas longe. Ele estava muito enganado.")
    total_visitantes = 0

    while True:
        try:
            visitante = input().strip()
        except EOFError:
            break

        if visitante == "ninguém":
            print("Ufa! Ninguém apareceu. Finalmente, um pouco de paz no pântano!")
            break

        # lê gasto de paciência
        try:
            gasto = int(input().strip())
        except EOFError:
            break

        assunto = None
        if visitante == "Burro":
            try:
                assunto = input().strip()
            except EOFError:
                assunto = ""

            if assunto == "sanduíche":
                gasto = gasto // 2

        # verifica se o gasto supera a paciência restante
        if gasto > paciencia:
            print("A paciência do Shrek acabou! Dê meia-volta antes que ele perca o controle!")
            break

        # visitante entra
        paciencia -= gasto
        total_visitantes += 1

        # mensagens específicas
        if visitante == "Burro":
            print("Burro?! Eu acabei de pedir um pouco de paz!")
            if assunto == "sanduíche":
                print("Ah, isso sim é um bom assunto!")
            elif assunto == "Fiona":
                print("É o Burro! E, como sempre, ele só sabe falar da Fiona.")
            elif assunto == "pântano":
                print("Burro, isso é MEU pântano...")
        elif visitante == "Gato de Botas":
            print("O Gato de Botas chegou! Shrek já está de olho nas suas botas.")
        elif visitante == "Pinóquio":
            print("Pinóquio chegou! Shrek espera que ele não esteja mentindo.")
        elif visitante == "Lobo Mau":
            print("Lobo Mau?! Shrek abriu a porta, mas já está se arrependendo!")
        else:
            print("Visitante desconhecido! Shrek não sabe quem você é, mas pode entrar por sua conta em risco.")

        # verifica se a paciência acabou exatamente
        if paciencia == 0:
            print("A paciência do Shrek acabou! Dê meia-volta antes que ele perca o controle!")
            break

    print(f"Ao todo, {total_visitantes} visitantes passaram pelo pântano. Shrek sobreviveu a mais um dia!")


if __name__ == "__main__":
    main()
