# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-20b, 17/10/2026.
# Só a partir do enunciado da L2-Q6, sem nenhum código de aluno. Revise antes do merge.
import sys

def main():
    try:
        ano_origem = int(sys.stdin.readline())
        ano_proibido = int(sys.stdin.readline())
        energia = int(sys.stdin.readline())
    except:
        return

    rasgo_temporal = 0
    pecas = 0
    ano_atual = ano_origem
    first_jump_done = False

    print("=== WABAC: SISTEMA DE EMERGÊNCIA ===")
    print("Alvo: Ano 2026 | Peças Necessárias: 3")
    print("Sherman, mantenha as mãos longe dos botões! Iniciando saltos...")

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        action = line.strip()

        # If abort command, break immediately
        if action == "ABORTAR":
            print("Mr. Peabody acionou o protocolo de parada manual.")
            print("A viagem foi cancelada antes de sua conclusão.")
            break

        if action == "SALTAR":
            anos_salto = int(sys.stdin.readline())
            custo_energia = int(sys.stdin.readline())
            ano_atual += anos_salto
            energia -= custo_energia
            rasgo_temporal += 10
            first_jump_done = True
        elif action == "CONSERTAR":
            dificuldade = int(sys.stdin.readline())
            esforco_sherman = int(sys.stdin.readline())
            if esforco_sherman >= dificuldade:
                pecas += 1
                energia -= 10
            else:
                energia -= 15
                rasgo_temporal += 20
        elif action == "AULA DE HISTÓRIA":
            energia += 25
            rasgo_temporal += 15

        # Normalização de limites
        if energia < 0:
            energia = 0
        if rasgo_temporal > 100:
            rasgo_temporal = 100

        # Check stopping conditions in priority order
        stopped = False
        # 1. Paradoxo das Duplicatas
        if ano_atual == ano_proibido or (ano_atual == ano_origem and first_jump_done):
            print(f"ALERTA CRÍTICO: Peabody encontrou sua própria versão no ano {ano_atual}!")
            print("O continuum espaço-tempo ruiu em uma espiral paradoxal.")
            stopped = True
        # 2. Apagão Temporal
        elif energia <= 0:
            print("A WABAC desligou completamente por falta de energia.")
            print("Peabody e Sherman estão vagando sem rumo pela linha do tempo...")
            stopped = True
        # 3. Colapso Dimensional
        elif rasgo_temporal >= 100:
            print("O rasgo temporal atingiu massa crítica!")
            print("O universo foi engolido por um buraco negro sobre a cidade de Nova York.")
            stopped = True
        # 5. Missão Cumprida
        elif pecas >= 3 and ano_atual >= 2026:
            print(f"A WABAC emergiu com sucesso no ano de {ano_atual}!")
            print("Com as 3 peças coletadas, Mr. Peabody selou o rasgo temporal e salvou o presente!")
            stopped = True

        if stopped:
            break

        # Print action-specific message
        if action == "SALTAR":
            print(f"WABAC saltou para o ano {ano_atual}!")
            print(f"Energia restante: {energia} | Rasgo Temporal: {rasgo_temporal}%")
        elif action == "CONSERTAR":
            if pecas > 0 and energia <= 10 + 15:  # not reliable; better track success
                # We can't determine success from state alone; we need to know if last action succeeded
                # Instead, we can track success in a variable
                pass
        # To handle CONSERTAR messages correctly, we need to know if success or failure
        # We'll modify the loop to store a flag

def main():
    try:
        ano_origem = int(sys.stdin.readline())
        ano_proibido = int(sys.stdin.readline())
        energia = int(sys.stdin.readline())
    except:
        return

    rasgo_temporal = 0
    pecas = 0
    ano_atual = ano_origem
    first_jump_done = False

    print("=== WABAC: SISTEMA DE EMERGÊNCIA ===")
    print("Alvo: Ano 2026 | Peças Necessárias: 3")
    print("Sherman, mantenha as mãos longe dos botões! Iniciando saltos...")

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        action = line.strip()

        # If abort command, break immediately
        if action == "ABORTAR":
            print("Mr. Peabody acionou o protocolo de parada manual.")
            print("A viagem foi cancelada antes de sua conclusão.")
            break

        success = None  # for CONSERTAR

        if action == "SALTAR":
            anos_salto = int(sys.stdin.readline())
            custo_energia = int(sys.stdin.readline())
            ano_atual += anos_salto
            energia -= custo_energia
            rasgo_temporal += 10
            first_jump_done = True
        elif action == "CONSERTAR":
            dificuldade = int(sys.stdin.readline())
            esforco_sherman = int(sys.stdin.readline())
            if esforco_sherman >= dificuldade:
                pecas += 1
                energia -= 10
                success = True
            else:
                energia -= 15
                rasgo_temporal += 20
                success = False
        elif action == "AULA DE HISTÓRIA":
            energia += 25
            rasgo_temporal += 15

        # Normalização de limites
        if energia < 0:
            energia = 0
        if rasgo_temporal > 100:
            rasgo_temporal = 100

        # Check stopping conditions in priority order
        stopped = False
        # 1. Paradoxo das Duplicatas
        if ano_atual == ano_proibido or (ano_atual == ano_origem and first_jump_done):
            print(f"ALERTA CRÍTICO: Peabody encontrou sua própria versão no ano {ano_atual}!")
            print("O continuum espaço-tempo ruiu em uma espiral paradoxal.")
            stopped = True
        # 2. Apagão Temporal
        elif energia <= 0:
            print("A WABAC desligou completamente por falta de energia.")
            print("Peabody e Sherman estão vagando sem rumo pela linha do tempo...")
            stopped = True
        # 3. Colapso Dimensional
        elif rasgo_temporal >= 100:
            print("O rasgo temporal atingiu massa crítica!")
            print("O universo foi engolido por um buraco negro sobre a cidade de Nova York.")
            stopped = True
        # 5. Missão Cumprida
        elif pecas >= 3 and ano_atual >= 2026:
            print(f"A WABAC emergiu com sucesso no ano de {ano_atual}!")
            print("Com as 3 peças coletadas, Mr. Peabody selou o rasgo temporal e salvou o presente!")
            stopped = True

        if stopped:
            break

        # Print action-specific message
        if action == "SALTAR":
            print(f"WABAC saltou para o ano {ano_atual}!")
            print(f"Energia restante: {energia} | Rasgo Temporal: {rasgo_temporal}%")
        elif action == "CONSERTAR":
            if success:
                print('Sherman: "Consegui, Mr. Peabody! Encontrei uma peça de calibragem!"')
                print(f"Peças coletadas: {pecas}/3 | Energia: {energia}")
            else:
                print('Mr. Peabody: "Tenha mais cuidado, Sherman! Essa falha desestabilizou o tempo!"')
                print(f"Energia: {energia} | Rasgo Temporal: {rasgo_temporal}%")
        elif action == "AULA DE HISTÓRIA":
            print('Mr. Peabody: "Como disse Galileu Galilei, a matemática é a linguagem com a qual Deus escreveu o universo."')
            print(f"Energia recarregada para {energia}!")

if __name__ == "__main__":
    main()
