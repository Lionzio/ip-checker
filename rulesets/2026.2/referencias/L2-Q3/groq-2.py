# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-120b, 17/10/2026.
# Só a partir do enunciado da L2-Q3, sem nenhum código de aluno. Revise antes do merge.
def main():
    try:
        paciencia = int(input())
    except EOFError:
        return

    print("Shrek achava que morar em um pântano afastado seria suficiente para manter as pessoas longe. Ele estava muito enganado.")
    total = 0

    while True:
        try:
            visitante = input().strip()
        except EOFError:
            break

        if visitante == "ninguém":
            print("Ufa! Ninguém apareceu. Finalmente, um pouco de paz no pântano!")
            break

        try:
            gasto = int(input())
        except EOFError:
            break

        assunto = None
        if visitante == "Burro":
            try:
                assunto = input().strip()
            except EOFError:
                assunto = ""
            if assunto == "sanduíche":
                gasto //= 2

        if gasto > paciencia:
            print("A paciência do Shrek acabou! Dê meia-volta antes que ele perca o controle!")
            break

        # visitante entra
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

        paciencia -= gasto
        total += 1

        if paciencia == 0:
            print("A paciência do Shrek acabou! Dê meia-volta antes que ele perca o controle!")
            break

    print(f"Ao todo, {total} visitantes passaram pelo pântano. Shrek sobreviveu a mais um dia!")

if __name__ == "__main__":
    main()
