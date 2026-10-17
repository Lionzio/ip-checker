# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L2-Q3, sem nenhum código de aluno. Revise antes do merge.
def main():
    paciencia = int(input())
    print("Shrek achava que morar em um pântano afastado seria suficiente para manter as pessoas longe. Ele estava muito enganado.")
    
    qtd_visitantes = 0
    
    while paciencia > 0:
        visitante = input()
        
        if visitante == "ninguém":
            print("Ufa! Ninguém apareceu. Finalmente, um pouco de paz no pântano!")
            break
            
        gasto = int(input())
        
        if visitante == "Burro":
            assunto = input()
            if assunto == "sanduíche":
                gasto = gasto / 2
                
        if gasto > paciencia or paciencia == 0:
            print("A paciência do Shrek acabou! Dê meia-volta antes que ele perca o controle!")
            break
            
        # Mensagens de recepção
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
            
        paciencia -= int(gasto)
        qtd_visitantes += 1
        
        if paciencia <= 0:
            print("A paciência do Shrek acabou! Dê meia-volta antes que ele perca o controle!")
            break
            
    print(f"Ao todo, {qtd_visitantes} visitantes passaram pelo pântano. Shrek sobreviveu a mais um dia!")

if __name__ == "__main__":
    main()
