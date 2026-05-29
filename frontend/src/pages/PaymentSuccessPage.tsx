import { Link } from 'react-router-dom';

export default function PaymentSuccessPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-green-50 to-white">
      <div className="text-center max-w-md mx-auto px-4">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <span className="text-3xl text-green-600">✓</span>
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-4">支付成功！</h1>
        <p className="text-gray-600 mb-8">
          感谢你的购买！你现在已解锁全部 AI 教师高级功能。
          开始你的中文学习之旅吧。
        </p>
        <Link
          to="/chat"
          className="inline-block bg-indigo-600 text-white px-8 py-3 rounded-xl font-semibold hover:bg-indigo-700 transition-all"
        >
          开始学习
        </Link>
      </div>
    </div>
  );
}
