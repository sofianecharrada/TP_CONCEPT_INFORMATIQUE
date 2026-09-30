import asyncio
import random
import time
import aiocoap
import aiocoap.resource as resource


class TemperatureResource(resource.ObservableResource):
    def __init__(self):
        super().__init__()
        self.value = 22.5
        self.notify = True

    async def render_get(self, request):
        return aiocoap.Message(
            code=aiocoap.Code.CONTENT,
            payload=str(self.value).encode()
        )

    async def render_put(self, request):
        try:
            self.value = float(request.payload.decode())
        except ValueError:
            return aiocoap.Message(code=aiocoap.Code.BAD_REQUEST)
        self.updated_state()
        return aiocoap.Message(code=aiocoap.Code.CHANGED)

    async def background_task(self):
        while True:
            await asyncio.sleep(2)
            self.value = round(20 + random.random() * 5, 1)
            self.updated_state()


class LedResource(resource.Resource):
    def __init__(self):
        super().__init__()
        self.etat = "off"

    async def render_get(self, request):
        return aiocoap.Message(code=aiocoap.Code.CONTENT, payload=self.etat.encode())

    async def render_put(self, request):
        nouvel_etat = request.payload.decode().strip().lower()
        if nouvel_etat not in ("on", "off"):
            return aiocoap.Message(code=aiocoap.Code.BAD_REQUEST, payload=b"use 'on' ou 'off'")
        self.etat = nouvel_etat
        return aiocoap.Message(code=aiocoap.Code.CHANGED)


class LogsResource(resource.Resource):
    def __init__(self):
        super().__init__()
        self.entries = []

    async def render_get(self, request):
        if not self.entries:
            payload = b"(aucun log)"
        else:
            payload = "\n".join(f"{i}: {e}" for i, e in enumerate(self.entries, 1)).encode()
        return aiocoap.Message(code=aiocoap.Code.CONTENT, payload=payload)

    async def render_post(self, request):
        texte = request.payload.decode()
        self.entries.append(f"[{time.strftime('%H:%M:%S')}] {texte}")
        message = aiocoap.Message(code=aiocoap.Code.CREATED)
        message.opt.location_path = ("logs", str(len(self.entries)))
        return message

    async def render_delete(self, request):
        self.entries.clear()
        return aiocoap.Message(code=aiocoap.Code.DELETED)


class TimeResource(resource.Resource):
    async def render_get(self, request):
        return aiocoap.Message(
            code=aiocoap.Code.CONTENT,
            payload=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()).encode()
        )


class SensorResource(resource.Resource):
    def __init__(self, valeur):
        super().__init__()
        self.valeur = valeur

    async def render_get(self, request):
        return aiocoap.Message(code=aiocoap.Code.CONTENT, payload=self.valeur.encode())


class BigLogResource(resource.Resource):
    async def render_get(self, request):
        lignes = "\n".join(f"Log {i}: capteur X - valeur {i*7 % 100}" for i in range(1, 61))
        return aiocoap.Message(code=aiocoap.Code.CONTENT, payload=lignes.encode())


async def main():
    racine = resource.Site()

    # Déclaration explicite de l'annuaire /.well-known/core
    racine.add_resource(
        (".well-known", "core"),
        resource.WKCResource(racine.get_resources_as_linkheader),
    )

    temp = TemperatureResource()
    racine.add_resource(("temp",), temp)
    racine.add_resource(("led",), LedResource())
    racine.add_resource(("logs",), LogsResource())
    racine.add_resource(("time",), TimeResource())

    # Module 3.2
    racine.add_resource(("sensors", "room1", "temperature"), SensorResource("23.5"))
    racine.add_resource(("sensors", "room1", "humidity"), SensorResource("55"))
    racine.add_resource(("sensors", "room1", "light"), SensorResource("150"))

    # Module 3.3
    racine.add_resource(("biglog",), BigLogResource())

    asyncio.get_running_loop().create_task(temp.background_task())

    await aiocoap.Context.create_server_context(racine, bind=("127.0.0.1", 5683))
    print("=== SERVEUR CoAP DÉMARRÉ (port UDP 5683) ===")
    print("Ctrl+C pour arrêter.")
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Serveur arrêté.")