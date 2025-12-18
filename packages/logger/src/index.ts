import { pino } from 'pino';

export const createLogger = (serviceName: string) => {
    return pino({
        name: serviceName,
        level: process.env.LOG_LEVEL || 'info',
        timestamp: pino.stdTimeFunctions.isoTime,
        formatters: {
            level: (label: string) => {
                return { level: label };
            },
        },
    });
};

export type Logger = pino.Logger;
