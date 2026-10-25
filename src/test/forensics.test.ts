import { describe, expect, it } from "vitest";
import { compareHashes, sha256Hex, validateFile, MAX_BYTES } from "@/lib/forensics";
describe("forensics", () => {
  it("sha256 of 'abc'", async () => {
    expect(await sha256Hex("abc")).toBe("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  });
  it("mismatch is failed, never passed", () => {
    expect(compareHashes("a", "b").state).toBe("failed");
    expect(compareHashes("a", "a").state).toBe("passed");
  });
  it("rejects files over 25 MB", () => {
    const f = new File([new Uint8Array(1)], "x.jpg", { type: "image/jpeg" });
    Object.defineProperty(f, "size", { value: MAX_BYTES + 1 });
    expect(validateFile(f)).toMatch(/25 MB/);
  });
});
