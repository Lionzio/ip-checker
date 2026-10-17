# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L2-Q6, sem nenhum código de aluno. Revise antes do merge.
def resolver():
    ano_origem = int(input())
    ano_proibido = int(input())
    energia = int(input())

    ano_atual = ano_origem
    rasgo_temporal = 0
    pecas = 0
    saltos_realizados = 0

    print("=== WABAC: SISTEMA DE EMERGÊNCIA ===")
    print("Alvo: Ano 2026 | Peças Necessárias: 3")
    print("Sherman, mantenha as mãos longe dos botões! Iniciando saltos...")

    motivo_parada = None

    while True:
        # Verificar condições de parada ANTES da ação (para paradoxo inicial após 1º salto, etc.)
        # Na verdade, a verificação ocorre após cada ação ou estado atualizado.
        # Vamos ler a ação:
        try:
            acao = input()
        except EOFError:
            break

        if acao == "SALTAR":
            anos_salto = int(input())
            custo_energia = int(input())

            ano_atual += anos_salto
            energia -= custo_energia
            rasgo_temporal += 10
            saltos_realizados += 1

        elif acao == "CONSERTAR":
            dificuldade = int(input())
            esforco_sherman = int(input())

            if esforco_sherman >= dificuldade:
                pecas += 1
                energia -= 10
            else:
                energia -= 15
                rasgo_temporal += 20

        elif acao == "AULA DE HISTÓRIA":
            energia += 25
            rasgo_temporal += 15

        elif acao == "ABORTAR":
            motivo_parada = "ABORTAR"
            break

        # Normalização de limites
        if energia < 0:
            energia = 0
        if rasgo_temporal > 100:
            rasgo_temporal = 100

        # Verificação de condições de parada na ordem de prioridade:
        # 1. Paradoxos: ano_atual == ano_proibido OU (saltos_realizados > 0 e ano_atual == ano_origem)
        if ano_atual == ano_proibido or (saltos_realizados > 0 and ano_atual == ano_origem):
            motivo_parada = "PARADOXO"
            break
        # 2. Apagão Temporal: energia <= 0
        elif energia <= 0:
            motivo_parada = "APAGAO"
            break
        # 3. Colapso Dimensional: rasgo_temporal >= 100
        elif rasgo_temporal >= 100:
            motivo_parada = "COLAPSO"
            break
        # 5. Missão Cumprida: pecas >= 3 E ano_atual >= 2026
        elif pecas >= 3 and ano_atual >= 2026:
            motivo_parada = "SUCESSO"
            break

        # Se a viagem continuar ativa, imprime a mensagem correspondente
        if acao == "SALTAR":
            print(f"WABAC saltou para o ano {ano_atual}!")
            print(f"Energia restante: {energia} | Rasgo Temporal: {rasgo_temporal}%")
        elif acao == "CONSERTAR":
            if esforco_sherman >= dificuldade:
                print('Sherman: "Consegui, Mr. Peabody! Encontrei uma peça de calibragem!"')
                print(f"Peças coletadas: {pecas}/3 | Energia: {energia}")
            else:
                print('Mr. Peabody: "Tenha mais cuidado, Sherman! Essa falha desestabilizou o tempo!"')
                print(f"Energia: {energia} | Rasgo Temporal: {rasgo_temporal}%")
        elif acao == "AULA DE HISTÓRIA":
            print('Mr. Peabody: "Como disse Galileu Galilei, a matemática é a linguagem com a qual Deus escreveu o universo."')
            print(f"Energia recarregada para {energia}!")

    # Mensagens finais
    if motivo_parada == "PARADOXO":
        print(f"ALERTA CRÍTICO: Peabody encontrou sua própria versão no ano {ano_atual}!")
        print("O continuum espaço-tempo ruiu em uma espiral paradoxal.")
    elif motivo_parada == "APAGAO":
        print("A WABAC desligou completamente por falta de energia.")
        print("Peabody e Sherman estão vagando sem rumo pela linha do tempo...")
    elif motivo_parada == "COLAPSO":
        print("O rasgo temporal atingiu massa crítica!")
        print("O universo foi engolido por um buraco negro sobre a cidade de Nova York.")
    elif motivo_parada == "ABORTAR":
        print("Mr. Peabody acionou o protocolo de parada manual.")
        print("A viagem foi cancelada antes de sua conclusão.")
    elif motivo_parada == "SUCESSO":
        print(f"A WABAC emergiu com sucesso no ano de {ano_atual}!")
        print("Com as 3 peças coletadas, Mr. Peabody selou o rasgo temporal e salvou o presente!")

resolver()
