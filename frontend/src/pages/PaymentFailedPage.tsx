import { Link } from 'react-router-dom';

export default function PaymentFailedPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-red-50 to-white">
      <div className="text-center max-w-md mx-auto px-4">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <span className="text-3xl text-red-500">✕</span>
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-4">支付未完成</h1>
        <p className="text-gray-600 mb-4">
          支付处理过程中出现了问题，你的账户未被扣款。
        </p>
        <p className="text-gray-500 text-sm mb-8">
          如果问题持续存在，请联系 support@qixie.tech
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            to="/plans"
            className="bg-indigo-600 text-white px-8 py-3 rounded-xl font-semibold hover:bg-indigo-700 transition-all"
          >
            重新选择套餐
          </Link>
          <Link
            to="/chat"
            className="border-2 border-gray-300 text-gray-700 px-8 py-3 rounded-xl font-semibold hover:border-gray-400 transition-all"
          >
            返回首页
          </Link>
        </div>
      </div>
    </div>
  );
}
