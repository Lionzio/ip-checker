# Solução gerada por IA (S42-04, ADR-08): qwen, modelo qwen/qwen3.8-27b, 17/10/2026.
# Só a partir do enunciado da L1-Q5, sem nenhum código de aluno. Revise antes do merge.
lugar = input()
pista = input()
suspeito = input()
alibi = input()

print("Um bom faro nunca falha! E o meu tá apontando pra uma covardia: sumiram TODOS os monitores! Eu passo o dia perseguindo o próprio rabo, mas juro que hoje acho eles mais rápido que isso!")

if lugar == "Grad 5":
    print("O laboratório mais movimentado do CIn... e nenhum sinal de monitor por aqui.")
elif lugar == "Kaonelle":
    print("Byte farejou cada mesa da Kaonelle em busca de pistas.")
elif lugar == "DA":
    print("A sala de convivência estava vazia. Até as bolinhas de ping pong sumiram.")
elif lugar == "Feirinha do CIn":
    print("No meio da Feirinha, muita gente, mas nenhum monitor à vista.")

if pista == "nota fiscal":
    if lugar == "Kaonelle":
        print("A nota fiscal é de uma compra de 350 cãoxinhas. Alguém está planejando alimentar um exército — ou uma festa e tanto.")
    else:
        print("Uma nota fiscal misteriosa, mas as informações estão meio apagadas.")
elif pista == "boné":
    print("Um boné caído no chão. Alguém saiu correndo e esqueceu a cabeça descoberta.")
elif pista == "balão":
    print("Um balão murcho no chão... isso aqui cheira a comemoração.")
elif pista == "passagem para Catende":
    print("Uma passagem de ônibus para Catende. Alguém tem raízes por lá.")

professores = ["Ricardo Maneiro", "Fernanda Arvore", "Marciano", "Amanda da Arte", "Yoda"]
if suspeito in professores:
    if pista == "balão" or (pista == "nota fiscal" and lugar == "Kaonelle"):
        print(f"{suspeito} alega o álibi: {alibi}. Diz estar ocupado com os preparativos de algo... mas não entrega do que se trata.")
    else:
        print(f"{suspeito} alega o álibi: {alibi}. Diz só estar corrigindo provas atrasadas. Nada a ver com o caso.")
elif suspeito == "Jaobé":
    if pista == "passagem para Catende":
        print(f"Diante da pista encontrada, Jaobé gagueja e alega o álibi: {alibi}. A coincidência é grande demais.")
    else:
        print(f"Jaobé alega o álibi: {alibi}. Sem essa pista específica, nada o liga ao caso.")
elif suspeito == "Jorge Arthur":
    if pista == "boné":
        print(f"Jorge Arthur alega o álibi: {alibi}... mas, estranhamente, está sem boné pela primeira vez na vida. Algo não bate.")
    else:
        print(f"Jorge Arthur alega o álibi: {alibi}. Sem essa pista específica, nada o liga ao caso.")

festa_cond = (suspeito in professores) and (pista == "balão" or (pista == "nota fiscal" and lugar == "Kaonelle")) and (alibi == lugar)
sequestro_cond = ((suspeito == "Jaobé" and pista == "passagem para Catende" and alibi == lugar) or (suspeito == "Jorge Arthur" and pista == "boné" and alibi == lugar))

if festa_cond:
    print("CASO ENCERRADO: Não houve crime algum! Os monitores, emocionados com a volta de Byte, prepararam uma festa surpresa, com direito a muita cãoxinha e bolinho de ração pra ele. O banquete foi ótimo... pelo menos pra quem é cachorro.")
elif sequestro_cond:
    print("CASO ENCERRADO: Jaobé e Jorge Arthur, enfurecidos por não terem honra o suficiente para serem conselheiros, sequestraram todos os monitores e só os libertariam em troca dos cargos. Byte percebe que o álibi contado bate exatamente com o lugar onde a pista foi encontrada, o flagrante perfeito! Byte morde a canela dos dois e resgata a equipe. Os culpados levam um puxão de orelha e são exilados da monitoria.")
else:
    print("CASO EM ABERTO: Byte se distraiu perseguindo um esquilo no meio do pátio e esqueceu completamente onde tinha parado a investigação. Sem solução dessa vez.")
