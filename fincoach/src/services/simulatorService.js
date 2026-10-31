import { request } from "./api";
export const simulateSip = (body) =>
  request("/simulator/sip", { method: "POST", body });
