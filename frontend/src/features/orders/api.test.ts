import { describe, expect, it } from "vitest";
import { minorUnits, money } from "./api";

describe("exact order display arithmetic", () => {
  it("keeps two-place decimal quantities exact through large NPR amounts", () => {
    expect(minorUnits("200.05") * 3n).toBe(60015n);
    expect(money(minorUnits("200.05") * 3n)).toBe("NPR 600.15");
    expect(minorUnits("99999999.99") * 99n).toBe(989999999901n);
    expect(money("0.00")).toBe("NPR 0.00");
  });
});
