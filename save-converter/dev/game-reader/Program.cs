using System.IO.Compression;
using System.Security.Cryptography;
using GamesByMalcs.Melvor2.Saves;

var body = new byte[20000];
new Random(7).NextBytes(body);
if (args[0] == "make")
{
    var header = new SaveHeader(SaveVersion.Alpha0_11_1_1, Guid.NewGuid(), "Garu Garu", "Standard", new DateTime(2026, 10, 19, 12, 0, 0), 1234, 5_000_000, 4_512, "Woodcutting", "res://Assets/wc.png", "Oak Tree", "res://Assets/oak.png", false);
    var memory = new MemoryStream();
    using (var brotli = new BrotliStream(memory, CompressionLevel.Optimal, true))
    using (var writer = new SaveWriter(brotli, SaveVersion.Alpha0_11_1_1))
    {
        writer.Write(header);
        writer.Write(body);
        writer.Flush();
    }
    File.WriteAllBytes(args[1], memory.ToArray());
    File.WriteAllText(args[2], Convert.ToBase64String(memory.ToArray()));
    Console.WriteLine($"made {header.UUID} body {Convert.ToHexString(SHA256.HashData(body))[..16]}");
}
else
{
    var raw = args[1].EndsWith(".txt") ? Convert.FromBase64String(File.ReadAllText(args[1])) : File.ReadAllBytes(args[1]);
    using var brotli = new BrotliStream(new MemoryStream(raw), CompressionMode.Decompress);
    using var reader = new SaveReader(brotli);
    var h = reader.Read<SaveHeader>();
    var rest = new MemoryStream();
    brotli.CopyTo(rest);
    Console.WriteLine($"read v{(int)h.Version} {h.UUID} '{h.CharacterName}' {h.Gamemode} {h.Timestamp:s} lvl {h.TotalLevel} gp {h.GP} sc {h.SlayerCoins} '{h.ActiveEntityName}' '{h.ActiveActionName}' IsDemo={h.IsDemo} corrupt={h.IsCorrupt} body {Convert.ToHexString(SHA256.HashData(rest.ToArray()))[..16]}");
}
