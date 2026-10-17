# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-20b, 17/10/2026.
# Só a partir do enunciado da L5-Q2, sem nenhum código de aluno. Revise antes do merge.
def main():
    import sys

    hero_order = ["Vax", "Pike", "Grog", "Percy", "Scanlan", "Vex", "Keyleth"]
    heroes = {h: [] for h in hero_order}
    order_counter = 0

    special_msgs = {
        ("Vex", "Fenthras"): "Um arco mágico, capaz de controlar todos os elementos? isso é perfeito para mim querido!",
        ("Grog", "Manoplas de Titanstone"): "Estou maior agora, e pronto para entrar em fúria!",
        ("Vax", "Adaga Mágica"): "Uma arma dada pela própria rainha dos corvos, agora apenas preciso saber se isso é uma dádiva ou uma maldição.",
        ("Scanlan", "Caça Mitos"): "A espada lendária capaz de matar todos os Dragões... nas mãos do Scanlan?!",
        ("Keyleth", "Pináculo da Confluência"): "Com isso e meu aramenté completo, a natureza inteira estará sobre meu controle.",
        ("Percy", "The List"): "Não, ele novamente não, Orthax já me dominou uma vez, não posso deixar isso acontecer de novo.",
        ("Pike", "Placa do Mártir"): "Everlight, espero que um dia você me perdoe, mas não vou mais depender de você."
    }

    for line in sys.stdin:
        line = line.strip()
        if line == "FIM":
            break
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 3:
            continue
        hero, weapon, power_str = parts
        try:
            power = int(power_str)
        except ValueError:
            continue
        if hero not in heroes:
            heroes[hero] = []
        heroes[hero].append((weapon, power, order_counter))
        order_counter += 1

        msg = special_msgs.get((hero, weapon))
        if msg:
            print(msg)

    for hero in hero_order:
        items = heroes.get(hero, [])
        if not items:
            print(f"{hero} não possui nenhuma arma.")
        else:
            best = items[0]
            for item in items[1:]:
                if item[1] > best[1] or (item[1] == best[1] and item[2] < best[2]):
                    best = item
            print(f"A arma mais forte de {hero} é a {best[0]} com {best[1]} Pontos de Poder.")


if __name__ == "__main__":
    main()
