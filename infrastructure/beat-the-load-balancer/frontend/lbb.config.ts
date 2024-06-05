export const main_vm_ips = {
    external: "localhost",
    internal: "10.2.0.4",
};

const isDevelopment = process.env.NODE_ENV === 'development';

console.log({ isDevelopment })

const main_ip = isDevelopment ? main_vm_ips.external : main_vm_ips.internal;

console.log({ main_ip })

const addPortToIp = (ip: string) => `http://${ip}:8000`

export const main_vm_address = addPortToIp(main_ip)
