// Gera o par de chaves da extensão e imprime a chave pública (para o "key" do manifest.json) e o ID
// que o Chrome deriva dela. A chave privada não é guardada: a extensão é instalada sem empacotar.
import { createHash, generateKeyPairSync } from "node:crypto";

const { publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
const der = publicKey.export({ type: "spki", format: "der" });
const hex = createHash("sha256").update(der).digest("hex").slice(0, 32);
const id = [...hex].map((c) => String.fromCharCode("a".charCodeAt(0) + parseInt(c, 16))).join("");
console.log(JSON.stringify({ key: der.toString("base64"), id }));
