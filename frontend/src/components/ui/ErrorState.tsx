export function ErrorState({ message = 'Something went wrong. Please try again.' }: { message?: string }) { return <div className="state error" role="alert">{message}</div> }
